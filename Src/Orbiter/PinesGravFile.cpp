/* Copyright(c) Matthew Hume and Orbiter contributors
 * Licensed under the MIT License
 * File access for the original Pines force calculation.
 */
#include "PinesGrav.h"
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <memory>
#include <string_view>
#if defined(__APPLE__)
#include <cerrno>
#include <cstdlib>
#include <locale.h>
#include <string>
#include <xlocale.h>
#endif

namespace {
std::uint64_t index(std::uint64_t n, std::uint64_t m) { return (n*n+n)/2+m; }
template<std::size_t N>
bool fields(std::string_view line, std::array<std::string_view, N>& result)
{
    for (std::size_t i = 0; i < N; ++i) {
        const auto comma = line.find(',');
        if (comma == std::string_view::npos && i+1 < N) return false;
        auto value = line.substr(0, comma);
        const auto first = value.find_first_not_of(" \t\r\n");
        if (first == std::string_view::npos) return false;
        value.remove_prefix(first);
        value = value.substr(0, value.find_last_not_of(" \t\r\n")+1);
        result[i] = value;
        if (comma != std::string_view::npos) line.remove_prefix(comma+1);
    }
    return true;
}
template<typename T> bool number(std::string_view text, T& result)
{
    if (text.empty()) return false;
    if (text.front() == '+') {
        text.remove_prefix(1);
        if (text.empty() || text.front() == '-' || text.front() == '+') return false;
    }
    const auto parsed = std::from_chars(text.data(), text.data()+text.size(), result);
    return parsed.ec == std::errc{} && parsed.ptr == text.data()+text.size();
}
#if defined(__APPLE__)
// Apple libc++ has integral from_chars support but lacks the floating overload
// on otherwise supported SDKs. Read the same bounded, locale-neutral tokens.
struct NumericLocale {
    locale_t handle = newlocale(LC_NUMERIC_MASK, "C", nullptr);
    ~NumericLocale() { if (handle) freelocale(handle); }
};

bool number(std::string_view text, double& result)
{
    static const NumericLocale locale;
    if (!locale.handle || text.empty() || text.find_first_not_of("0123456789.eE+-") != std::string_view::npos)
        return false;
    const std::string token(text);
    char* end = nullptr;
    errno = 0;
    const double value = strtod_l(token.c_str(), &end, locale.handle);
    const bool outOfRange = errno == ERANGE && (value == 0 || !std::isfinite(value));
    if (end != token.c_str()+token.size() || outOfRange) return false;
    result = value;
    return true;
}
#endif
}

int PinesGravProp::readGravModel(char* filename, int cutoff, int& loaded, int& maximum)
{
    if (!filename) return 1;
    return ReadGravityModel(std::filesystem::path(filename), cutoff, loaded, maximum);
}

int PinesGravProp::ReadGravityModel(const std::filesystem::path& filename, int cutoff,
    int& actualLoadedTerms, int& maxModelTerms)
{
    // Keep the legacy result codes: 1=open, 2=allocation, 3=header, 4=coefficients.
    // Parse into temporary storage so failure/reload never leaks or publishes
    // a partially loaded force model. The force and recurrence code is unchanged.
    if (cutoff < 0) return 3;
    std::ifstream input(filename, std::ios::binary);
    if (!input) return 1;
    char line[512];
    if (!input.getline(line, sizeof(line))) return 3;
    double radius, parameter, uncertainty, latitude, longitude;
    unsigned modelOrder, modelDegree, modelNormalized;
    std::array<std::string_view, 8> header;
    if (!fields(line, header) || !number(header[0], radius) || !number(header[1], parameter) ||
        !number(header[2], uncertainty) || !number(header[3], modelOrder) || !number(header[4], modelDegree) ||
        !number(header[5], modelNormalized) || !number(header[6], latitude) || !number(header[7], longitude) ||
        !std::isfinite(radius) || radius <= 0 || !std::isfinite(parameter) || parameter <= 0 ||
        !std::isfinite(uncertainty) || !std::isfinite(latitude) || !std::isfinite(longitude) || modelNormalized != 1) return 3;
    const auto maximum = index(modelOrder, modelDegree);
    if (maximum > static_cast<std::uint64_t>(std::numeric_limits<int>::max())) return 3;
    // Preserve the original cutoff calculation for the coefficient file's limit.
    auto cutoffLines = index(static_cast<unsigned>(cutoff), static_cast<unsigned>(cutoff));
    unsigned effectiveCutoff = static_cast<unsigned>(cutoff);
    if (maximum < cutoffLines) {
        cutoffLines = maximum;
        effectiveCutoff = static_cast<unsigned>(std::lround((std::sqrt(9+8*cutoffLines)-3)/2));
    }
    const auto count = index(effectiveCutoff, effectiveCutoff);
    if (count > cutoffLines) return 3;
    // Four comma-separated values need at least seven bytes per record plus
    // a separator. Reject impossible/truncated files before trusting their
    // declared dimensions for memory allocation.
    const auto coefficientsBegin = input.tellg();
    input.seekg(0, std::ios::end);
    const auto remaining = input.tellg()-coefficientsBegin;
    input.seekg(coefficientsBegin);
    if (!input || remaining < 0 || (count && static_cast<std::uint64_t>(remaining) < count*8-1)) return 4;
    // NM in the unchanged recurrence uses unsigned arithmetic. Reject sizes
    // that it cannot represent before allocation or coefficient indexing.
    const std::uint64_t upper = static_cast<std::uint64_t>(effectiveCutoff)+3;
    if (upper*upper+upper > std::numeric_limits<unsigned>::max()) return 2;
    const auto coefficientCount = index(effectiveCutoff+1, effectiveCutoff+1);
    const auto legendreCount = index(upper, upper);
    if (legendreCount > std::numeric_limits<std::size_t>::max()/sizeof(double)) return 2;
    try {
        std::unique_ptr<double[]> c(new double[static_cast<std::size_t>(coefficientCount)]);
        std::unique_ptr<double[]> s(new double[static_cast<std::size_t>(coefficientCount)]);
        std::unique_ptr<double[]> real(new double[static_cast<std::size_t>(effectiveCutoff)+2]);
        std::unique_ptr<double[]> imaginary(new double[static_cast<std::size_t>(effectiveCutoff)+2]);
        std::unique_ptr<double[]> legendre(new double[static_cast<std::size_t>(legendreCount)]);
        c[0] = s[0] = 0; // The original algorithm excludes point-mass gravity.
        for (std::uint64_t next = 1; next <= count; ++next) {
            if (!input.getline(line, sizeof(line))) return 4;
            unsigned n, m;
            std::array<std::string_view, 4> coefficient;
            if (!fields(line, coefficient) || !number(coefficient[0], n) || !number(coefficient[1], m) ||
                !number(coefficient[2], c[next]) || !number(coefficient[3], s[next]) ||
                m > n || index(n, m) != next || !std::isfinite(c[next]) || !std::isfinite(s[next])) return 4;
        }
        delete[] C; delete[] S; delete[] R; delete[] I; delete[] A;
        C = c.release(); S = s.release(); R = real.release(); I = imaginary.release(); A = legendre.release();
        refRad = radius; GM = parameter; order = modelOrder; degree = modelDegree;
        normalized = modelNormalized; referenceLat = latitude; referenceLon = longitude;
        CoeffCutoff = effectiveCutoff;
        numCoeff = static_cast<unsigned long>(count+1);
        actualLoadedTerms = static_cast<int>(count);
        maxModelTerms = static_cast<int>(maximum);
        return 0;
    } catch (const std::bad_alloc&) {
        return 2;
    }
}
