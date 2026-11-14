// Licensed under the MIT License
// Decode color blocks on the CPU only when Orbiter copies a stock DDS onto
// a mutable surface during vessel startup. The Vulkan draw uses BC textures.
namespace {

using Color = std::array<std::uint8_t, 4>;

Color Color565(unsigned pixel)
{
    const unsigned r = (pixel >> 11) & 31;
    const unsigned g = (pixel >> 5) & 63;
    const unsigned b = pixel & 31;
    return {std::uint8_t((r << 3) | (r >> 2)), std::uint8_t((g << 2) | (g >> 4)),
        std::uint8_t((b << 3) | (b >> 2)), 255};
}

Color Mix(const Color& a, const Color& b, unsigned weightA, unsigned weightB)
{
    Color out{};
    for (unsigned c = 0; c < 4; ++c)
        out[c] = std::uint8_t((a[c] * weightA + b[c] * weightB) / (weightA + weightB));
    return out;
}

Color ReadPixel(const TextureData& texture, unsigned x, unsigned y)
{
    if (!texture.blockBytes) {
        const auto* pixel = texture.pixels.data() + (std::size_t(y) * texture.width + x) * 4;
        if (texture.format == SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM)
            return {pixel[2], pixel[1], pixel[0], pixel[3]};
        return {pixel[0], pixel[1], pixel[2], pixel[3]};
    }

    const auto stride = (texture.width + 3) / 4;
    const auto* block = texture.pixels.data() + ((y / 4) * stride + x / 4) * texture.blockBytes;
    const auto* rgb = block + (texture.blockBytes == 16 ? 8 : 0);
    const unsigned c0 = rgb[0] | (rgb[1] << 8);
    const unsigned c1 = rgb[2] | (rgb[3] << 8);
    const bool transparent = texture.blockBytes == 8 && c0 <= c1;
    const Color first = Color565(c0);
    const Color second = Color565(c1);
    const Color palette[] = {first, second, transparent ? Mix(first, second, 1, 1) : Mix(first, second, 2, 1),
        transparent ? Color{} : Mix(first, second, 1, 2)};
    const auto i = (y % 4) * 4 + x % 4;
    Color result = palette[(rgb[4 + i / 4] >> (i % 4 * 2)) & 3];
    if (texture.format == SDL_GPU_TEXTUREFORMAT_BC2_RGBA_UNORM)
        result[3] = std::uint8_t(((block[i / 2] >> (4 * (i % 2))) & 15) * 17);
    if (texture.format == SDL_GPU_TEXTUREFORMAT_BC3_RGBA_UNORM) {
        std::uint64_t codes = 0;
        for (unsigned j = 0; j < 6; ++j) codes |= std::uint64_t(block[2 + j]) << (j * 8);
        const auto code = unsigned((codes >> (i * 3)) & 7);
        if (code < 2) result[3] = block[code];
        else if (block[0] > block[1]) result[3] = std::uint8_t(((8 - code) * block[0] + (code - 1) * block[1]) / 7);
        else if (code < 6) result[3] = std::uint8_t(((6 - code) * block[0] + (code - 1) * block[1]) / 5);
        else result[3] = code == 6 ? 0 : 255;
    }
    return result;
}

} // namespace
