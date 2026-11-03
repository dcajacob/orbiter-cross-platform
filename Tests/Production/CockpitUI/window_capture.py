"""Capture this test's owned X11 window, including on a rootless XWayland server."""
import ctypes as C
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent/'Client')]
from run_client import png


class XImage(C.Structure):
    _fields_ = [('width', C.c_int), ('height', C.c_int), ('xoffset', C.c_int),
                ('format', C.c_int), ('data', C.c_void_p), ('byte_order', C.c_int),
                ('bitmap_unit', C.c_int), ('bitmap_bit_order', C.c_int), ('bitmap_pad', C.c_int),
                ('depth', C.c_int), ('bytes_per_line', C.c_int), ('bits_per_pixel', C.c_int),
                ('red_mask', C.c_ulong), ('green_mask', C.c_ulong), ('blue_mask', C.c_ulong),
                ('obdata', C.c_void_p), ('functions', C.c_void_p*6)]


def capture(xlib, display, window, output):
    xlib.XGetGeometry.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_ulong),
        C.POINTER(C.c_int), C.POINTER(C.c_int), C.POINTER(C.c_uint),
        C.POINTER(C.c_uint), C.POINTER(C.c_uint), C.POINTER(C.c_uint)]
    xlib.XGetGeometry.restype = C.c_int
    xlib.XGetImage.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_int,
                             C.c_uint, C.c_uint, C.c_ulong, C.c_int]
    xlib.XGetImage.restype = C.POINTER(XImage)
    xlib.XDestroyImage.argtypes = [C.POINTER(XImage)]
    xlib.XDestroyImage.restype = C.c_int
    root, left, top = C.c_ulong(), C.c_int(), C.c_int()
    width, height, border, depth = (C.c_uint() for _ in range(4))
    if not xlib.XGetGeometry(display, window, C.byref(root), C.byref(left), C.byref(top),
                            C.byref(width), C.byref(height), C.byref(border), C.byref(depth)):
        raise ValueError('Cannot read the owned capture window geometry')
    if not (0 < width.value <= 8192 and 0 < height.value <= 8192):
        raise ValueError('Invalid owned capture window dimensions')
    image = xlib.XGetImage(display, window, 0, 0, width, height, C.c_ulong(-1).value, 2)
    if not image:
        raise ValueError('Cannot capture the owned application window')
    try:
        info = image.contents
        masks = (info.red_mask, info.green_mask, info.blue_mask)
        if (info.width != width.value or info.height != height.value or info.xoffset != 0 or
                info.format != 2 or info.bits_per_pixel not in (16, 24, 32) or not all(masks)):
            raise ValueError('Unsupported owned-window XImage layout')
        step = info.bits_per_pixel//8
        if info.bytes_per_line < info.width*step or not info.data:
            raise ValueError('Incomplete owned-window image')
        source = C.string_at(info.data, info.bytes_per_line*info.height)
        rgba = bytearray(b'\xff'*(info.width*info.height*4))
        shifts = [(mask & -mask).bit_length()-1 for mask in masks]
        byte_channels = all(mask == 255 << shift and shift % 8 == 0 for mask, shift in zip(masks, shifts))
        for y in range(info.height):
            row = source[y*info.bytes_per_line:y*info.bytes_per_line+info.width*step]
            # The existing real-client PNG writer accepts bottom-up RGBA.
            destination = (info.height-1-y)*info.width*4
            if byte_channels:
                for channel, shift in enumerate(shifts):
                    index = shift//8 if info.byte_order == 0 else step-1-shift//8
                    rgba[destination+channel:destination+info.width*4:4] = row[index::step]
            else:
                for pixel in range(info.width):
                    value = int.from_bytes(row[pixel*step:(pixel+1)*step], 'little' if info.byte_order == 0 else 'big')
                    for channel, (mask, shift) in enumerate(zip(masks, shifts)):
                        rgba[destination+pixel*4+channel] = ((value & mask) >> shift)*255//(mask >> shift)
        png(output, rgba, info.width, info.height)
    finally:
        xlib.XDestroyImage(image)
