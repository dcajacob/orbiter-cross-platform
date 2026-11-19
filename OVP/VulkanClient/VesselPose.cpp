// Licensed under the MIT License
#include "VesselPose.h"

#include <algorithm>
#include <cmath>
#include <map>

namespace orbiter::vulkan {
namespace {

const SceneFrame identity{{}, {{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}}};

VECTOR3 Cross(const VECTOR3& a, const VECTOR3& b)
{
    return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}

VECTOR3 Normalized(const VECTOR3& v)
{
    const double length = std::sqrt(Dot(v, v));
    return length > 0 ? Scale(v, 1 / length) : v;
}

SceneFrame Compose(const SceneFrame& outer, const SceneFrame& inner)
{
    return {outer.ToGlobal(inner.origin),
        {outer.Rotate(inner.axes[0]), outer.Rotate(inner.axes[1]), outer.Rotate(inner.axes[2])}};
}

struct Component {
    VECTOR3 anchor{};
    VECTOR3 axis{};
    double angle = 0;
};

Component Copy(const MGROUP_TRANSFORM& source)
{
    switch (source.Type()) {
    case MGROUP_TRANSFORM::ROTATE: {
        const auto& rotation = static_cast<const MGROUP_ROTATE&>(source);
        return {rotation.ref, rotation.axis, rotation.angle};
    }
    case MGROUP_TRANSFORM::TRANSLATE:
        return {{}, static_cast<const MGROUP_TRANSLATE&>(source).shift, 0};
    case MGROUP_TRANSFORM::SCALE: {
        const auto& scale = static_cast<const MGROUP_SCALE&>(source);
        return {scale.ref, scale.scale, 0};
    }
    default:
        return {};
    }
}

SceneFrame Transform(const MGROUP_TRANSFORM& source, const Component& component, double from, double to)
{
    auto transform = identity;
    switch (source.Type()) {
    case MGROUP_TRANSFORM::ROTATE: {
        const auto axis = Normalized(component.axis);
        const double angle = (to - from) * component.angle;
        const double c = std::cos(angle);
        const double s = std::sin(angle);
        for (auto& basis : transform.axes) {
            basis = Add(Add(Scale(basis, c), Scale(Cross(axis, basis), s)),
                Scale(axis, Dot(basis, axis) * (1 - c)));
        }
        break;
    }
    case MGROUP_TRANSFORM::TRANSLATE:
        transform.origin = Scale(component.axis, to - from);
        return transform;
    case MGROUP_TRANSFORM::SCALE: {
        const auto ratio = [from, to](double scale) {
            const double before = 1 + from * (scale - 1);
            return before != 0 ? (1 + to * (scale - 1)) / before : 1;
        };
        transform.axes = {{{ratio(component.axis.x), 0, 0}, {0, ratio(component.axis.y), 0},
            {0, 0, ratio(component.axis.z)}}};
        break;
    }
    default:
        return transform;
    }
    transform.origin = Subtract(component.anchor, transform.Rotate(component.anchor));
    return transform;
}

using Parameters = std::map<const MGROUP_TRANSFORM*, Component>;

Component& ParameterFor(Parameters& parameters, const MGROUP_TRANSFORM* component)
{
    auto it = parameters.find(component);
    if (it == parameters.end()) it = parameters.emplace(component, Copy(*component)).first;
    return it->second;
}

void Apply(const ANIMATIONCOMP& component, const SceneFrame& transform, Parameters& parameters,
    const std::vector<MeshGroups>& meshes, std::vector<SceneFrame>& groups, std::vector<bool>& changed)
{
    const auto& source = *component.trans;
    if (source.mesh < meshes.size()) {
        const auto& mesh = meshes[source.mesh];
        const auto applyGroup = [&](std::size_t index) {
            if (index >= mesh.count) return;
            const auto group = mesh.first + index;
            groups[group] = Compose(transform, groups[group]);
            changed[group] = true;
        };
        if (source.grp) {
            for (unsigned i = 0; i < source.ngrp; ++i) applyGroup(source.grp[i]);
        } else {
            for (std::size_t group = 0; group < mesh.count; ++group) applyGroup(group);
        }
    }
    for (unsigned i = 0; i < component.nchildren; ++i) {
        const auto& child = *component.children[i];
        Apply(child, transform, parameters, meshes, groups, changed);
        auto& parameter = ParameterFor(parameters, child.trans);
        if (child.trans->Type() == MGROUP_TRANSFORM::ROTATE) {
            parameter.anchor = transform.ToGlobal(parameter.anchor);
            parameter.axis = Normalized(transform.Rotate(parameter.axis));
        } else if (child.trans->Type() == MGROUP_TRANSFORM::TRANSLATE) {
            parameter.axis = transform.Rotate(parameter.axis);
        } else if (child.trans->Type() == MGROUP_TRANSFORM::SCALE) {
            parameter.anchor = transform.ToGlobal(parameter.anchor);
        }
    }
}

void PoseGroup(std::vector<Vertex>& posed, const VertexRange& range, const SceneFrame& transform)
{
    const auto& axes = transform.axes;
    auto normals = SceneFrame{{}, {Cross(axes[1], axes[2]), Cross(axes[2], axes[0]), Cross(axes[0], axes[1])}};
    if (Dot(axes[0], normals.axes[0]) < 0) {
        for (auto& axis : normals.axes) axis = Scale(axis, -1);
    }
    for (std::size_t i = range.first; i < range.first + range.count; ++i) {
        auto& v = posed[i];
        const auto position = transform.ToGlobal({v.position[0], v.position[1], v.position[2]});
        const auto normal = Normalized(normals.Rotate({v.normal[0], v.normal[1], v.normal[2]}));
        v.position[0] = float(position.x); v.position[1] = float(position.y); v.position[2] = float(position.z);
        v.normal[0] = float(normal.x); v.normal[1] = float(normal.y); v.normal[2] = float(normal.z);
    }
}

} // namespace

void VesselPose::Reset(std::vector<Vertex> mesh, std::vector<VertexRange> groups, std::vector<MeshGroups> meshes)
{
    meshes_ = std::move(meshes);
    mesh_ = std::move(mesh);
    groups_ = std::move(groups);
    posed_ = mesh_;
    states_.clear();
    initialized_ = false;
}

bool VesselPose::Update(const VESSEL& vessel)
{
    ANIMATION* data = nullptr;
    const auto count = vessel.GetAnimPtr(&data);
    bool changed = !initialized_ || states_.size() != count;
    states_.resize(count);
    for (unsigned i = 0; i < count; ++i) {
        changed |= states_[i] != data[i].state;
        states_[i] = data[i].state;
    }
    for (unsigned index = 0; index < meshes_.size(); ++index) {
        auto& mesh = meshes_[index];
        if (!mesh.count) continue;
        VECTOR3 offset{};
        vessel.GetMeshOffset(index, offset);
        changed |= offset.x != mesh.offset.x || offset.y != mesh.offset.y || offset.z != mesh.offset.z;
        mesh.offset = offset;
    }
    if (!changed || mesh_.empty()) return false;
    initialized_ = true;
    posed_ = mesh_;

    Parameters parameters;
    std::vector<SceneFrame> transforms(groups_.size(), identity);
    std::vector<bool> moved(groups_.size(), false);
    for (unsigned i = 0; i < count; ++i) {
        const auto& animation = data[i];
        if (animation.state == animation.defstate) continue;
        // Compose each stock animation from its mesh default. Reversing from
        // the default reverses component order, including child pivots.
        for (unsigned j = 0; j < animation.ncomp; ++j) {
            const auto& component = *animation.comp[animation.state > animation.defstate ? j : animation.ncomp-j-1];
            const double span = component.state1 - component.state0;
            if (span <= 0) continue;
            const auto from = std::clamp((animation.defstate - component.state0) / span, 0.0, 1.0);
            const auto to = std::clamp((animation.state - component.state0) / span, 0.0, 1.0);
            if (from == to) continue;
            const auto transform = Transform(*component.trans, ParameterFor(parameters, component.trans), from, to);
            Apply(component, transform, parameters, meshes_, transforms, moved);
        }
    }
    for (const auto& mesh : meshes_) {
        const bool offset = Dot(mesh.offset, mesh.offset) != 0;
        for (auto i = mesh.first; i < mesh.first + mesh.count; ++i) {
            if (!moved[i] && !offset) continue;
            // Animation pivots are mesh-local. Place the posed group in vessel space last.
            transforms[i].origin = Add(transforms[i].origin, mesh.offset);
            PoseGroup(posed_, groups_[i], transforms[i]);
        }
    }
    return true;
}

} // namespace orbiter::vulkan
