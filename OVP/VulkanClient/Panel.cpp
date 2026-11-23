// Licensed under the MIT License
#include "OrbiterScene.h"

#include <algorithm>
#include <limits>

namespace orbiter::vulkan {

void OrbiterScene::Panel(SURFHANDLE* surfaces, MESHHANDLE mesh, const MATRIX3& tx,
    float alpha, bool additive, const std::function<SURFHANDLE(int)>& mfd)
{
    constexpr auto defaultTexture = std::numeric_limits<unsigned>::max();
    auto slot = defaultTexture;
    for (unsigned i = 0; mesh && i < oapiMeshGroupCount(mesh); ++i) {
        const auto* g = oapiMeshGroup(mesh, i);
        if (!g || (g->UsrFlag & 2) || !g->nIdx) continue;
        if (g->TexIdx != defaultTexture - 1) slot = g->TexIdx;
        SURFHANDLE handle = nullptr;
        if (slot != defaultTexture) {
            handle = slot >= TEXIDX_MFD0 ? mfd(int(slot - TEXIDX_MFD0)) :
                (surfaces ? surfaces[slot] : oapiGetTextureHandle(mesh, slot + 1));
            if (!Lookup(handle)) continue;
        }
        scene_.PanelGroup(Lookup(handle), *g, tx, alpha, additive);
    }
}

void Scene::OpenPanel(SDL_GPUShader* vertex, SDL_GPUShader* fragment)
{
    panelWhite_.width = panelWhite_.height = 1;
    panelWhite_.pixels.assign(4, 255);
    SDL_GPUVertexBufferDescription buffer{};
    buffer.pitch = sizeof(PanelVertex);
    SDL_GPUVertexAttribute attribute{0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4, 0};
    SDL_GPUColorTargetDescription target{};
    target.format = SDL_GetGPUSwapchainTextureFormat(device_, window_);
    auto& blend = target.blend_state;
    blend.enable_blend = true;
    blend.src_color_blendfactor = SDL_GPU_BLENDFACTOR_SRC_ALPHA;
    blend.src_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE;
    blend.dst_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
    blend.color_blend_op = blend.alpha_blend_op = SDL_GPU_BLENDOP_ADD;
    SDL_GPUGraphicsPipelineCreateInfo info{};
    info.vertex_shader = vertex;
    info.fragment_shader = fragment;
    info.vertex_input_state = {&buffer, 1, &attribute, 1};
    info.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
    info.target_info.color_target_descriptions = &target;
    info.target_info.num_color_targets = 1;
    info.target_info.has_depth_stencil_target = true;
    info.target_info.depth_stencil_format = depthFormat_;
    for (unsigned i = 0; i < 2; ++i) {
        blend.dst_color_blendfactor = i ? SDL_GPU_BLENDFACTOR_ONE : SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
        panelPipeline_[i] = SDL_CreateGPUGraphicsPipeline(device_, &info);
        Require(panelPipeline_[i] != nullptr, "Create instrument panel pipeline");
    }
}

void Scene::PanelGroup(const TextureData* image, const MESHGROUP& group, const MATRIX3& tx,
    float alpha, bool additive)
{
    const auto first = Uint32(panelVertices_.size());
    for (unsigned i = 0; i < group.nIdx; ++i) {
        if (group.Idx[i] >= group.nVtx) {
            panelVertices_.resize(first);
            return;
        }
        const auto& v = group.Vtx[group.Idx[i]];
        panelVertices_.push_back({float(v.x*tx.m11 + v.y*tx.m12 + tx.m13),
            float(v.x*tx.m21 + v.y*tx.m22 + tx.m23), v.tu, v.tv});
    }
    panelBatches_.push_back({image ? image : &panelWhite_, first, group.nIdx, alpha, additive});
}

void Scene::PreparePanel()
{
    if (panelBuffer_) SDL_ReleaseGPUBuffer(device_, panelBuffer_);
    panelBuffer_ = nullptr;
    if (panelVertices_.empty()) return;
    panelBuffer_ = UploadBuffer(SDL_GPU_BUFFERUSAGE_VERTEX, panelVertices_.data(),
        panelVertices_.size() * sizeof(PanelVertex));
    for (const auto& batch : panelBatches_) {
        PanelTextureFor(batch.image);
    }
}

SDL_GPUTexture* Scene::PanelTextureFor(const TextureData* image)
{
    if (!image) return nullptr;
    auto& cached = panelTextures_[image];
    if (!cached.gpu || cached.revision != image->revision) {
        auto* fresh = UploadTexture(*image);
        RetirePanelTexture(cached.gpu);
        cached = {fresh, image->revision};
    }
    return cached.gpu;
}

void Scene::RetirePanelTexture(SDL_GPUTexture* texture)
{
    if (!texture) return;
    // ImGui draw lists can still contain this handle until presentation.
    if (guiInitialized_) retiredPanelTextures_.push_back(texture);
    else SDL_ReleaseGPUTexture(device_, texture);
}

void Scene::ReleaseRetiredPanelTextures()
{
    for (auto* texture : retiredPanelTextures_) SDL_ReleaseGPUTexture(device_, texture);
    retiredPanelTextures_.clear();
}

void Scene::DrawPanel(SDL_GPURenderPass* pass, SDL_GPUCommandBuffer* cmd, unsigned w, unsigned h)
{
    if (!panelBuffer_) return;
    const float scale[4]{2.0f/w, -2.0f/h};
    SDL_PushGPUVertexUniformData(cmd, 0, scale, sizeof(scale));
    const SDL_GPUBufferBinding vertices{panelBuffer_, 0};
    SDL_BindGPUVertexBuffers(pass, 0, &vertices, 1);
    for (const auto& batch : panelBatches_) {
        SDL_BindGPUGraphicsPipeline(pass, panelPipeline_[batch.additive]);
        const SDL_GPUTextureSamplerBinding binding{panelTextures_.at(batch.image).gpu, terrainSampler_};
        SDL_BindGPUFragmentSamplers(pass, 0, &binding, 1);
        const float paint[4]{batch.alpha};
        SDL_PushGPUFragmentUniformData(cmd, 0, paint, sizeof(paint));
        SDL_DrawGPUPrimitives(pass, batch.count, 1, batch.first, 0);
    }
}

void Scene::ForgetPanelTexture(const TextureData* image)
{
    const auto found = panelTextures_.find(image);
    if (found != panelTextures_.end()) {
        RetirePanelTexture(found->second.gpu);
        panelTextures_.erase(found);
    }
    panelBatches_.erase(std::remove_if(panelBatches_.begin(), panelBatches_.end(),
        [image](const PanelBatch& batch) { return batch.image == image; }), panelBatches_.end());
}

void Scene::ClearPanel() noexcept
{
    panelVertices_.clear();
    panelBatches_.clear();
    while (!panelTextures_.empty()) ForgetPanelTexture(panelTextures_.begin()->first);
    if (panelBuffer_) SDL_ReleaseGPUBuffer(device_, panelBuffer_);
    panelBuffer_ = nullptr;
}

} // namespace orbiter::vulkan
