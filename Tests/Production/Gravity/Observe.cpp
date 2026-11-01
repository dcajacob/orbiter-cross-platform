// Licensed under the MIT License
// Observation driver for the unchanged production Pines implementation.
#include "Vecmat.h"
#include "PinesGrav.h"
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <locale>
#include <stdexcept>
#include <string>

int main(int argc, char** argv)
{
    try {
        if (argc != 5 || std::string(argv[1]) != "--data-root" || std::string(argv[3]) != "--output")
            throw std::runtime_error("Usage: production-gravity-observer --data-root <checkout> --output <csv>");
        const auto root = std::filesystem::absolute(argv[2]);
        std::ofstream output(argv[4], std::ios::binary);
        output.imbue(std::locale::classic());
        output.exceptions(std::ios::badbit | std::ios::failbit);
        output << std::setprecision(17)
            << "model,degree,order,sample,loaded_terms,max_terms,x_km,y_km,z_km,ax_m_s2,ay_m_s2,az_m_s2\n";
        const std::array<std::array<double, 3>, 12> directions{{
            {1,0,0}, {-1,0,0}, {0,1,0}, {0,-1,0}, {0,0,1}, {0,0,-1},
            {.6,.8,0}, {-.6,.8,0}, {.6,0,.8}, {0,-.6,.8}, {.36,.48,.8}, {1e-12,0,1}
        }};
        struct Model { const char* name; const char* file; double radius; };
        const std::array<Model, 2> models{{
            {"Earth", "GravityModels/egm96_to360.tab", 7000},
            {"Moon", "GravityModels/jgl165p1.sha", 2000}
        }};
        // Independent closed-form check of a normalized, J2-only model.
        // This supplementary model does not replace either stock input.
        {
            PinesGravProp j2(nullptr);
            auto path = (root / "Tests/Production/Gravity/J2.tab").string();
            int loaded = 0, maximum = 0;
            if (j2.readGravModel(path.data(), 2, loaded, maximum) != 0 || loaded != 5 || maximum != 5)
                throw std::runtime_error("Cannot load the analytical J2 fixture");
            constexpr double mu = 398600.4415, referenceRadius = 6378.1363, coefficient = .001;
            for (const auto& direction : directions) {
                const Vector p(7000*direction[0], 7000*direction[1], 7000*direction[2]);
                const double r = p.length(), z2 = p.z*p.z/(r*r);
                const double factor = 1.5*coefficient*mu*referenceRadius*referenceRadius/std::pow(r, 5);
                const Vector expected(factor*p.x*(5*z2-1), factor*p.y*(5*z2-1), factor*p.z*(5*z2-3));
                const double error = (j2.GetPinesGrav(p, 2, 2)-expected).length()*1000;
                if (!std::isfinite(error) || error > 1e-12)
                    throw std::runtime_error("Production Pines fails the independent J2 solution");
            }
        }
        unsigned sample = 0;
        for (const auto& model : models) {
            PinesGravProp gravity(nullptr);
            auto path = (root / model.file).string();
            int loaded = 0, maximum = 0;
            if (gravity.readGravModel(path.data(), 32, loaded, maximum) != 0 ||
                gravity.GetCoeffCutoff() != 32 || loaded != 560 || maximum < loaded)
                throw std::runtime_error("Cannot load the required production gravity model: " + path);
            for (const int degree : {2, 4, 12, 32})
                for (const int order : {0, degree / 2, degree})
                    for (const double altitude : {1., 2., 10.})
                        for (const auto& direction : directions) {
                            // Actual Pines contract: right-handed body-fixed km;
                            // perturbation only, converted from km/s^2 to SI here.
                            const double radius = model.radius * altitude;
                            const Vector position(radius * direction[0], radius * direction[1], radius * direction[2]);
                            const Vector acceleration = gravity.GetPinesGrav(position, degree, order) * 1000.;
                            if (!std::isfinite(acceleration.x) || !std::isfinite(acceleration.y) ||
                                !std::isfinite(acceleration.z))
                                throw std::runtime_error("Nonfinite production gravity observation");
                            output << model.name << ',' << degree << ',' << order << ',' << sample++ << ','
                                << loaded << ',' << maximum << ',' << position.x << ',' << position.y << ',' << position.z << ','
                                << acceleration.x << ',' << acceleration.y << ',' << acceleration.z << '\n';
                        }
        }
        output.close();
        std::cout << "Observed " << sample << " production Pines queries\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
