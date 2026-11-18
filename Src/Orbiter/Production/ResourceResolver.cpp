// Licensed under the MIT License
#include "ResourceResolver.h"
#include <stdexcept>
#include <vector>

namespace orbiter::production {
namespace fs = std::filesystem;

std::string ResourceResolver::Normalize(const std::string& relative)
{
    if (relative.empty()) throw std::invalid_argument("Empty resource path");
    std::string key;
    std::string component;
    auto append = [&] {
        if (component == "..") throw std::invalid_argument("Resource path escapes its root: " + relative);
        if (!component.empty() && component != ".") {
            if (!key.empty()) key += '/';
            key += component;
        }
        component.clear();
    };
    if (relative.front() == '/' || relative.front() == '\\')
        throw std::invalid_argument("Resource path must be relative: " + relative);
    for (unsigned char c : relative) {
        if (c == '/' || c == '\\') append();
        else {
            if (c == ':' || c == 0 || c < 32)
                throw std::invalid_argument("Invalid resource path: " + relative);
            component += static_cast<char>(c >= 'A' && c <= 'Z' ? c + ('a' - 'A') : c);
        }
    }
    append();
    if (key.empty()) throw std::invalid_argument("Empty resource path: " + relative);
    return key;
}

ResourceResolver::ResourceResolver(const fs::path& directory)
    : root(fs::canonical(directory))
{
    if (!fs::is_directory(root)) throw std::runtime_error("Resource root is not a directory: " + root.string());
    std::map<std::string, fs::path> names;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        const auto relative = entry.path().lexically_relative(root);
        const auto key = Normalize(relative.generic_string());
        auto inserted = names.emplace(key, relative);
        if (!inserted.second)
            throw std::runtime_error("Conflicting case aliases: " + inserted.first->second.string() + " and " + relative.string());
        // A symlink can otherwise bypass both the alias index and the root.
        // Explicitly reject it rather than silently omit required resources.
        if (entry.is_symlink()) throw std::runtime_error("Symlink in resource root: " + relative.string());
        if (entry.is_regular_file()) files.emplace(key, entry.path());
        else if (entry.is_directory()) directories.emplace(key,entry.path());
        else throw std::runtime_error("Unsupported resource entry: " + relative.string());
    }
}

void ResourceResolver::SelectVariant(const std::string& target,const std::string& source)
{
    const auto key = Normalize(target);
    const auto from = source.empty() ? std::string{} : Normalize(source);
    if (key == from) return;
    if (!from.empty() && !files.count(from) && !directories.count(from))
        throw std::runtime_error("Missing resource variant: " + source);
    // Both trees are siblings. Keep their original paths for opening the files.
    if (!from.empty() && fs::path(key).parent_path() != fs::path(from).parent_path())
        throw std::invalid_argument("Expected sibling resource variants");
    auto select = [&](auto& index) {
        index.erase(key);
        const auto prefix = key + "/";
        auto it = index.lower_bound(prefix);
        while (it != index.end() && it->first.compare(0,prefix.size(),prefix) == 0)
            it = index.erase(it);
        if (from.empty()) return;
        auto entry = index.find(from);
        if (entry != index.end()) index.emplace(key,entry->second);
        const auto sourcePrefix = from + "/";
        for (it = index.lower_bound(sourcePrefix); it != index.end() &&
             it->first.compare(0,sourcePrefix.size(),sourcePrefix) == 0; ++it)
            index.emplace(key + it->first.substr(from.size()),it->second);
    };
    select(files);
    select(directories);
}

fs::path ResourceResolver::Resolve(const std::string& relative) const
{
    const auto found = files.find(Normalize(relative));
    if (found == files.end()) throw std::runtime_error("Missing resource: " + relative + " under " + root.string());
    return found->second;
}
bool ResourceResolver::Contains(const std::string& relative) const
{
    return files.count(Normalize(relative)) != 0;
}
fs::path ResourceResolver::ResolveDirectory(const std::string& relative) const
{
    const auto found=directories.find(Normalize(relative));
    if (found==directories.end()) throw std::runtime_error("Missing resource directory: "+relative+" under "+root.string());
    return found->second;
}
bool ResourceResolver::ContainsDirectory(const std::string& relative) const
{
    return directories.count(Normalize(relative))!=0;
}
}
