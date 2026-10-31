// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_RESOURCE_RESOLVER_H
#define ORBITER_PRODUCTION_RESOURCE_RESOLVER_H
#include "Export.h"
#include <filesystem>
#include <map>
#include <string>

namespace orbiter::production {
// Index one explicit, read-only resource root. Callers choose roots for Config,
// Meshes, Textures, Kernels, etc.; this never searches the working directory.
// The original spelling is retained for opening files on case-sensitive hosts.
class ORBITER_PRODUCTION_API ResourceResolver {
public:
    explicit ResourceResolver(const std::filesystem::path& root);
    std::filesystem::path Resolve(const std::string& relative) const;
    bool Contains(const std::string& relative) const;
    const std::filesystem::path& Root() const { return root; }
    std::size_t FileCount() const { return files.size(); }
    static std::string Normalize(const std::string& relative);
private:
    std::filesystem::path root;
    std::map<std::string, std::filesystem::path> files;
};
}
#endif
