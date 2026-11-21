"""Author the DG forward console and interior canopy hardware as Open CASCADE solids.

Arguments are an existing DG virtual cockpit mesh and an output directory.
All design dimensions are millimetres. The final MSH uses Orbiter metres.
"""

import argparse
from collections import Counter, defaultdict
from math import cos, sin, radians
from pathlib import Path

import numpy as np
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepLib import BRepLib
from OCP.BRepLib import BRepLib_ToolTriangulatedShape
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.GC import GC_MakeArcOfCircle
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt, gp_Vec

from finishes import swatch, fascia_uv, bezel_uv, write_textures


def unit(v):
    return v / np.linalg.norm(v)


def polygon(points):
    builder = BRepBuilderAPI_MakePolygon()
    for p in points:
        builder.Add(gp_Pnt(*p))
    builder.Close()
    return builder.Wire()


class Plane:
    def __init__(self, origin, right, up, front):
        self.o, self.x, self.y, self.n = map(np.array, (origin, right, up, front))

    def point(self, x, y, d=0):
        return self.o + x * self.x + y * self.y + d * self.n

    def xy(self, p):
        delta = p - self.o
        return delta @ self.x, delta @ self.y

    def outline(self, xy, d):
        return polygon([self.point(x, y, d) for x, y in xy])

    def bore(self, x, y, radius):
        axis = gp_Ax2(gp_Pnt(*self.point(x, y)), gp_Dir(*np.cross(self.x, self.y)), gp_Dir(*self.x))
        edge = BRepBuilderAPI_MakeEdge(gp_Circ(axis, radius)).Edge()
        return BRepBuilderAPI_MakeWire(edge).Wire()

    def roundrect(self, x, y, width, height, radius, depth):
        # Four tangent circular arcs with straight runs between them.
        w, h = width / 2, height / 2
        centres = (
            (w - radius, h - radius),
            (-w + radius, h - radius),
            (-w + radius, -h + radius),
            (w - radius, -h + radius),
        )
        arcs = []
        for i, (cx, cy) in enumerate(centres):

            def at(angle):
                a = radians(90 * i + angle)
                return gp_Pnt(
                    *self.point(x + cx + radius * cos(a), y + cy + radius * sin(a), depth)
                )

            arcs.append((at(0), at(45), at(90)))
        wire = BRepBuilderAPI_MakeWire()
        for i, (start, mid, end) in enumerate(arcs):
            wire.Add(BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(start, mid, end).Value()).Edge())
            wire.Add(BRepBuilderAPI_MakeEdge(end, arcs[(i + 1) % 4][0]).Edge())
        return wire.Wire()


def extrusion(wire, vector, holes=()):
    face = BRepBuilderAPI_MakeFace(wire)
    for hole in holes:
        face.Add(TopoDS.Wire(hole.Reversed()))
    return BRepPrimAPI_MakePrism(face.Face(), gp_Vec(*vector)).Shape()


def loft(a, b):
    builder = BRepOffsetAPI_ThruSections(True, True)
    builder.CheckCompatibility(False)
    builder.AddWire(a)
    builder.AddWire(b)
    builder.Build()
    return builder.Shape()


class Console:
    def __init__(self):
        self.parts = []

    def add(self, shape, finish, mapper=None):
        it = TopExp_Explorer(shape, TopAbs_SOLID)
        if not it.More() or not BRepCheck_Analyzer(shape).IsValid():
            raise ValueError(f"Invalid {finish} solid")
        solid = TopoDS.Solid(it.Current())
        if not BRepLib.OrientClosedSolid_s(solid):
            raise ValueError(f"Open {finish} body")
        self.parts.append((solid, finish, mapper))

    def screw(self, plane, x, y, depth, radius=2.0):
        # A recessed hex socket leaves a real opening in the head.
        def ring(r, levels):
            return plane.outline(
                [
                    (x + r * cos(radians(i * 360 / levels)), y + r * sin(radians(i * 360 / levels)))
                    for i in range(levels)
                ],
                depth,
            )

        self.add(extrusion(ring(radius, 16), plane.n * 0.45, [ring(radius * 0.45, 6)]), "fastener")

    def glareshield(self):
        p = Plane((0, 1240, 7268), (1, 0, 0), (0, 1, 0), (0, 0, -1))
        border = [(-276, 1), (276, 1), (276, 29), (92, 77), (-92, 77), (-276, 29)]

        def slot(x, y, w, h, r=1.5):
            return p.roundrect(x, y, w, h, r, 0)

        # Original button caps, rotary controls and their full travel pass through here.
        holes = [
            slot(0, 53.5, 59, 17),
            p.bore(-10, 30, 11.4),
            slot(16.5, 31, 12, 12),
            p.bore(65, 37, 13),
            p.outline(
                [
                    (99, 15),
                    (181, 15),
                    (181, 33),
                    (161, 33),
                    (161, 47),
                    (119, 47),
                    (119, 33),
                    (99, 33),
                ],
                0,
            ),
        ]
        for x in (-175, -153, -131, -109, -87):
            holes.append(slot(x, 23, 17, 3.4, 1.3))
        self.add(
            extrusion(p.outline(border, 0), p.n * 1.05, holes),
            "fascia",
            lambda point: fascia_uv(*p.xy(point)),
        )
        for x, y in [(-269, 8), (-269, 26), (-94, 69), (91, 69), (270, 26), (270, 8)]:
            self.screw(p, x, y, 1.06, 2.4)
        # A padded brow follows the three top edges of the existing glare shield.
        for (x0, y0), (x1, y1) in zip(border[2:5], border[3:6]):

            def section(x, y):
                return polygon(
                    [
                        p.point(x, y + v, d)
                        for v, d in [
                            (0, 1),
                            (0, 5),
                            (1.2, 7.3),
                            (3.5, 8.1),
                            (5.0, 6.2),
                            (5.1, 0),
                            (3, -1),
                        ]
                    ]
                )

            self.add(loft(section(x0, y0), section(x1, y1)), "padding")

    def mfd(self, side):
        a = radians(20)
        p = Plane(
            (side * 165, 1151.415, 7265.63), (1, 0, 0), (0, cos(a), sin(a)), (0, sin(a), -cos(a))
        )
        d = 11.6
        outer = p.roundrect(0, -8, 210, 202, 5, d)
        holes = [
            p.roundrect(0, 0, 169.5, 169.5, 2, d),
            p.roundrect(-95, -1, 19.6, 136, 2, d),
            p.roundrect(95, -1, 19.6, 136, 2, d),
            p.roundrect(0, -96, 43, 19, 2, d),
        ]
        self.add(
            extrusion(outer, -p.n * 3.4, holes), "bezel", lambda point: bezel_uv(side, *p.xy(point))
        )
        # A tapered aperture connects the lip to the recessed live display.
        # Split into four shallow rails. Each section keeps the original screen clear.
        for horizontal in (False, True):
            for sign in (-1, 1):

                def section(end):
                    result = []
                    for span, offset, depth in [
                        (82.0, 82.0, 1.0),
                        (85.3, 85.3, 9.2),
                        (85.3, 85.3, 11.8),
                        (84.8, 84.8, 12.6),
                        (83.4, 83.4, 12.4),
                        (80.9, 80.9, 1.1),
                    ]:
                        x, y = (
                            (end * span, sign * offset)
                            if horizontal
                            else (sign * offset, end * span)
                        )
                        result.append(p.point(x, y, depth))
                    return polygon(result)

                self.add(loft(section(-1), section(1)), "gasket")
        for x in (-100, 100):
            for y in (-101, 86):
                self.screw(p, x, y, d + 0.02, 2.1)

    def canopy(self, lines):
        groups = [i for i, s in enumerate(lines) if s.startswith("GEOM ")]
        eye = np.array([0, 1467, 6782])
        for g in (36, 37, 38):
            k = groups[g]
            n, m = map(int, lines[k].split()[1:3])
            coords = np.array([list(map(float, s.split()[:3])) for s in lines[k + 1 : k + 1 + n]])
            pos, idx = np.unique(coords.round(4), axis=0, return_inverse=True)
            triangles = [list(map(int, s.split()[:3])) for s in lines[k + n + 1 : k + n + m + 1]]
            edges = Counter(
                tuple(sorted((a, b)))
                for tri in idx[triangles]
                for a, b in zip(tri, np.roll(tri, -1))
            )
            adj = defaultdict(list)
            for (a, b), count in edges.items():
                if count == 1:
                    adj[a].append(b)
                    adj[b].append(a)
            loops = []
            remaining = set(adj)
            while remaining:
                start = min(remaining)
                cur = start
                loop = []
                while cur in remaining:
                    loop.append(cur)
                    remaining.remove(cur)
                    cur = next((v for v in adj[cur] if v in remaining), start)
                loops.append(pos[loop] * 1000)
            # The densely sampled loop borders the pane; the other borders the cabin shell.
            rim = max(loops, key=len)
            centre = rim.mean(axis=0)
            normal = unit(np.cross(rim - centre, np.roll(rim, -1, axis=0) - centre).sum(axis=0))
            if normal @ (eye - centre) < 0:
                normal = -normal
            outward = []
            for i, q in enumerate(rim):
                edge0 = unit(np.cross(q - rim[i - 1], normal))
                edge1 = unit(np.cross(rim[(i + 1) % len(rim)] - q, normal))
                v = unit(edge0 + edge1)
                outward.append(v * np.sign(v @ (q - centre)) / abs(v @ edge0))
            for i, q in enumerate(rim):
                j = (i + 1) % len(rim)
                for finish, profile in [
                    ("gasket", [(-1, -1), (-1, 1.7), (0.5, 3.4), (4, 4.0), (6, 2.5), (6, -1)]),
                    (
                        "rail",
                        [
                            (5, 0),
                            (5, 3.8),
                            (7, 5.6),
                            (14, 5.9),
                            (18, 4.2),
                            (19, 1),
                            (19, -1),
                            (5, -1),
                        ],
                    ),
                ]:

                    def section(k):
                        return polygon([rim[k] + outward[k] * w + normal * h for w, h in profile])

                    self.add(loft(section(i), section(j)), finish)
                length = np.linalg.norm(rim[j] - q)
                if length > 56:
                    axis = unit(rim[j] - q)
                    for f in np.linspace(0, 1, round(length / 95) + 2)[1:-1]:
                        anchor = (
                            q * (1 - f)
                            + rim[j] * f
                            + unit(outward[i] * (1 - f) + outward[j] * f) * 12
                        )
                        self.screw(
                            Plane(anchor, axis, unit(np.cross(normal, axis)), normal), 0, 0, 6, 2.45
                        )

    def export(self, dest, lines):
        assembly = TopoDS_Compound()
        builder = BRep_Builder()
        builder.MakeCompound(assembly)
        batches = [([], []), ([], [])]
        for body, finish, mapper in self.parts:
            builder.Add(assembly, body)
            BRepMesh_IncrementalMesh(body, 0.18, False, 0.30)
            faces = TopExp_Explorer(body, TopAbs_FACE)
            verts, tris = batches[int(mapper is not None)]
            while faces.More():
                face = TopoDS.Face(faces.Current())
                loc = TopLoc_Location()
                mesh = BRep_Tool.Triangulation_s(face, loc)
                BRepLib_ToolTriangulatedShape.ComputeNormals_s(face, mesh)
                rev = face.Orientation() == TopAbs_REVERSED
                first = len(verts) - 1
                for j in range(1, mesh.NbNodes() + 1):
                    pos = mesh.Node(j).Transformed(loc.Transformation())
                    q = np.array(pos.Coord())
                    normal = mesh.Normal(j).Transformed(loc.Transformation())
                    if rev:
                        normal.Reverse()
                    uv = mapper(q) if mapper else swatch(finish)
                    verts.append((*q * 0.001, *normal.Coord(), *uv))
                for j in range(1, mesh.NbTriangles() + 1):
                    a, b, c = mesh.Triangle(j).Get()
                    tris.append((first + a, first + (c if rev else b), first + (b if rev else c)))
                faces.Next()
        step = STEPControl_Writer()
        if (
            step.Transfer(assembly, STEPControl_AsIs) != IFSelect_RetDone
            or step.Write(str(dest / "DG-flight-deck.step")) != IFSelect_RetDone
        ):
            raise ValueError("STEP export failed")
        a = lines.index("MATERIALS 29") if "MATERIALS 29" in lines else lines.index("MATERIALS 31")
        if "GROUPS 135" in lines:
            a = lines.index("LABEL ConsoleHardware")
            del lines[a : lines.index("MATERIALS 31")]
        else:
            lines[lines.index("GROUPS 133")] = "GROUPS 135"
            lines[a] = "MATERIALS 31"
            first = next(i for i in range(a + 1, len(lines)) if lines[i].startswith("MATERIAL "))
            names = ["ConsoleHardware", "ConsoleFaceplates"]
            lines[first:first] = names
            t = lines.index("TEXTURES 20")
            lines[t] = "TEXTURES 21"
            for name in reversed(names):
                lines[t:t] = [
                    "MATERIAL " + name,
                    "1 1 1 1",
                    "0.7 0.7 0.7 1",
                    "0.18 0.18 0.18 1 28",
                    "0.06 0.06 0.06 1",
                ]
            lines.append(r"DG\dg_flightdeck.dds")
        out = []
        for index, ((verts, tris), name) in enumerate(
            zip(batches, ["ConsoleHardware", "ConsoleFaceplates"])
        ):
            out.extend(
                [
                    "LABEL " + name,
                    "MATERIAL " + str(30 + index),
                    "TEXTURE 21",
                    "FLAG 1",
                    f"GEOM {len(verts)} {len(tris)}",
                ]
            )
            out.extend(" ".join(f"{v:.6f}" for v in vertex) for vertex in verts)
            out.extend("%d %d %d" % tri for tri in tris)
        lines[a:a] = out
        (dest / "deltaglider_vc.msh").write_text("\n".join(lines) + "\n")
        print(
            f"{len(self.parts)} validated closed solids; {sum(len(t) for v, t in batches)} triangles"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.mesh.read_text().splitlines()
    kit = Console()
    kit.glareshield()
    kit.mfd(-1)
    kit.mfd(1)
    kit.canopy(source)
    kit.export(args.output, source)
    write_textures(args.output)
