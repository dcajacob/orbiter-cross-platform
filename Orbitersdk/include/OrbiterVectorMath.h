// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_VECTOR_MATH_H
#define ORBITER_VECTOR_MATH_H
#include "OrbiterGeometry.h"
#include <math.h>

/**
 * \ingroup vec
 * \brief Vector composition
 *
 * Returns a vector composed of the three provided arguments
 * \param x x-component
 * \param y y-component
 * \param z z-component
 * \return vector defined as (x,y,z)
 */
inline VECTOR3 _V(double x, double y, double z)
{
	VECTOR3 vec = {x,y,z}; return vec;
}

/**
 * \ingroup vec
 * \brief Vector copy
 *
 * Copies the element values from the source to the target vector.
 * \param[out] a target vector
 * \param[in] b source vector
 */
inline void veccpy (VECTOR3 &a, const VECTOR3 &b)
{
	a.x = b.x;
	a.y = b.y;
	a.z = b.z;
}

/**
 * \ingroup vec
 * \brief Vector addition
 * \param a first vector operand
 * \param b second vector operand
 * \return Result of a+b.
 */
inline VECTOR3 operator+ (const VECTOR3 &a, const VECTOR3 &b)
{
	VECTOR3 c;
	c.x = a.x+b.x;
	c.y = a.y+b.y;
	c.z = a.z+b.z;
	return c;
}

/**
 * \ingroup vec
 * \brief Vector subtraction
 * \param a first vector operand
 * \param b second vector operand
 * \return Result of a-b.
 */
inline VECTOR3 operator- (const VECTOR3 &a, const VECTOR3 &b)
{
	VECTOR3 c;
	c.x = a.x-b.x;
	c.y = a.y-b.y;
	c.z = a.z-b.z;
	return c;
}

/**
 * \ingroup vec
 * \brief Multiplication of vector with scalar
 * \param a vector operand
 * \param f scalar operand
 * \return Result of element-wise a*f.
 */
inline VECTOR3 operator* (const VECTOR3 &a, const double f)
{
	VECTOR3 c;
	c.x = a.x*f;
	c.y = a.y*f;
	c.z = a.z*f;
	return c;
}

/**
 * \ingroup vec
 * \brief Division of vector by a scalar
 * \param a vector operand
 * \param f scalar operand
 * \return Result of element-wise a/f.
 */
inline VECTOR3 operator/ (const VECTOR3 &a, const double f)
{
	VECTOR3 c;
	c.x = a.x/f;
	c.y = a.y/f;
	c.z = a.z/f;
	return c;
}

/**
 * \ingroup vec
 * \brief Vector addition-assignment a += b
 * \param[in,out] a Left-hand vector operand
 * \param[in] b Right-hand vector operand
 * \return Replaces a with a+b and returns the result.
 */
inline VECTOR3 &operator+= (VECTOR3 &a, const VECTOR3 &b)
{
	a.x += b.x;
	a.y += b.y;
	a.z += b.z;
	return a;
}

/**
 * \ingroup vec
 * \brief Vector subtraction-assignment a -= b
 * \param[in,out] a Left-hand vector operand
 * \param[in] b Right-hand vector operand
 * \return Replaces a with a-b and returns the result.
 */
inline VECTOR3 &operator-= (VECTOR3 &a, const VECTOR3 &b)
{
	a.x -= b.x;
	a.y -= b.y;
	a.z -= b.z;
	return a;
}

/**
 * \ingroup vec
 * \brief Vector-scalar multiplication-assignment a *= f
 * \param[in,out] a Left-hand vector operand
 * \param[in] f Right hand scalar operand
 * \return Replaces a with element-wise a*f and returns the result.
 */
inline VECTOR3 &operator*= (VECTOR3 &a, const double f)
{
	a.x *= f;
	a.y *= f;
	a.z *= f;
	return a;
}

/**
 * \ingroup vec
 * \brief Vector-scalar division-assignment a /= f
 * \param[in,out] a Left-hand vector operand
 * \param[in] f Right-hand scalar operand
 * \return Replaces a with element-wise a/f and returns the result.
 */
inline VECTOR3 &operator/= (VECTOR3 &a, const double f)
{
	a.x /= f;
	a.y /= f;
	a.z /= f;
	return a;
}

/**
 * \ingroup vec
 * \brief Vector unary minus -a
 * \param[in] a Vector operand
 * \return Negative vector (-a.x, -a.y, -a.z)
 */
inline VECTOR3 operator- (const VECTOR3 &a)
{
	VECTOR3 c;
	c.x = -a.x;
	c.y = -a.y;
	c.z = -a.z;
	return c;
}

/**
 * \ingroup vec
 * \brief Scalar (inner, dot) product of two vectors
 * \param[in] a First vector operand
 * \param[in] b Second vector operand
 * \return Scalar product <b>ab</b>
 */
inline double dotp (const VECTOR3 &a, const VECTOR3 &b)
{
	return a.x*b.x + a.y*b.y + a.z*b.z;
}

/**
 * \ingroup vec
 * \brief Vector (cross) product of two vectors
 * \param[in] a First vector operand
 * \param[in] b Second vector operand
 * \return Vector product <b>a</b>x<b>b</b>
 */
inline VECTOR3 crossp (const VECTOR3 &a, const VECTOR3 &b)
{
	return _V(a.y*b.z - b.y*a.z, a.z*b.x - b.z*a.x, a.x*b.y - b.x*a.y);
}

/**
 * \ingroup vec
 * \brief Length (L2-norm) of a vector
 * \param a Vector operand
 * \return Vector norm |<b>a</b>|<sub>2</sub>
 */
inline double length (const VECTOR3 &a)
{
	return sqrt (a.x*a.x + a.y*a.y + a.z*a.z);
}

/**
 * \ingroup vec
 * \brief Length squared of a vector
 * \param a Vector operand
 * \return Vector norm |<b>a</b>|<sub>2</sub><sup>2</sup>
 */
inline double length2 (const VECTOR3 &a)
{
	return (a.x*a.x + a.y*a.y + a.z*a.z);
}

/**
 * \ingroup vec
 * \brief Distance between two points
 * \param[in] a First point
 * \param[in] b Second point
 * \return Distance between a and b
 */
inline double dist (const VECTOR3 &a, const VECTOR3 &b)
{
	return length (a-b);
}

/**
 * \ingroup vec
 * \brief Normalise a vector
 *
 * Resizes the argument vector to length 1.
 * \param[in,out] a Vector argument
 * \note The length of a must be greater than 0.
 */
inline void normalise (VECTOR3 &a)
{
	a /= length(a);
}

/**
 * \ingroup vec
 * \brief Returns normalised vector
 *
 * Returns a vector of length 1 with the same direction
 * as the argument vector.
 * \param[in] a Vector argument
 * \return Normalised vector.
 * \note The length of a must be greater than 0.
 */
inline VECTOR3 unit (const VECTOR3 &a)
{
	return a / length(a);
}

/**
 * \ingroup vec
 * \brief Matrix composition
 *
 * Returns a matrix composed of the provided elements.
 * \return
 * \f$
 *  \left(\begin{array}{ccc}
 *  m_{11} & m_{12} & m_{13} \\
 *  m_{21} & m_{22} & m_{23} \\
 *  m_{31} & m_{32} & m_{33}
 *  \end{array}\right)
 * \f$
 */
inline MATRIX3 _M(double m11, double m12, double m13,
				  double m21, double m22, double m23,
				  double m31, double m32, double m33)
{
	MATRIX3 mat = {m11,m12,m13,  m21,m22,m23,  m31,m32,m33};
	return mat;
}

/**
 * \ingroup vec
 * \brief Returns the identity matrix
 */
inline MATRIX3 identity ()
{
	static MATRIX3 mat = {1,0,0, 0,1,0, 0,0,1};
	return mat;
}

/**
 * \ingroup vec
 * \brief Return transpose of a matrix
 */
inline MATRIX3 transp(const MATRIX3& M)
{
	return _M(M.m11, M.m21, M.m31,
		      M.m12, M.m22, M.m32,
		      M.m13, M.m23, M.m33);
}

/**
 * \ingroup vec
 * \brief Outer product of two vectors
 * \param[in] a First vector operand
 * \param[in] b Second vector operand
 * \return Outer product <b>a</b><b>b</b><sup>T</sup>, where
 * <b>a</b> and <b>b</b> represent column vectors.
 */
inline MATRIX3 outerp (const VECTOR3 &a, const VECTOR3 &b)
{
	return _M(a.x*b.x, a.x*b.y, a.x*b.z,
		      a.y*b.x, a.y*b.y, a.y*b.z,
			  a.z*b.x, a.z*b.y, a.z*b.z);
}

/**
 * \ingroup vec
 * \brief Sum of matrix and scalar.
 * \param[in] A Matrix operand (left)
 * \param[in] s scalar operand (right)
 * \return A+s (element-wise sum of A and s)
 */
inline MATRIX3 operator+ (const MATRIX3 &A, double s)
{
	MATRIX3 mat = {A.m11+s, A.m12+s, A.m13+s,
		           A.m21+s, A.m22+s, A.m23+s,
				   A.m31+s, A.m32+s, A.m33+s};
	return mat;
}

/**
 * \ingroup vec
 * \brief Difference of matrix and scalar.
 * \param[in] A Matrix operand (left)
 * \param[in] s scalar operand (right)
 * \return A-s (element-wise difference of A and s)
 */
inline MATRIX3 operator- (const MATRIX3 &A, double s)
{
	MATRIX3 mat = {A.m11-s, A.m12-s, A.m13-s,
		           A.m21-s, A.m22-s, A.m23-s,
				   A.m31-s, A.m32-s, A.m33-s};
	return mat;
}

/**
 * \ingroup vec
 * \brief Product of matrix and scalar.
 * \param[in] A Matrix operand (left)
 * \param[in] s scalar operand (right)
 * \return A*s (element-wise product of A and s)
 */
inline MATRIX3 operator* (const MATRIX3 &A, double s)
{
	MATRIX3 mat = {A.m11*s, A.m12*s, A.m13*s,
		           A.m21*s, A.m22*s, A.m23*s,
				   A.m31*s, A.m32*s, A.m33*s};
	return mat;
}

/**
 * \ingroup vec
 * \brief Quotient of matrix and scalar.
 * \param[in] A Matrix operand (left)
 * \param[in] s scalar operand (right)
 * \return A/s (element-wise quotient of A and s)
 * \note s != 0 is required.
 */
inline MATRIX3 operator/ (const MATRIX3 &A, double s)
{
	MATRIX3 mat = {A.m11/s, A.m12/s, A.m13/s,
		           A.m21/s, A.m22/s, A.m23/s,
				   A.m31/s, A.m32/s, A.m33/s};
	return mat;
}

/**
 * \ingroup vec
 * \brief Matrix-scalar product-assignment A *= s
 * \param[in] A Matrix operand (left)
 * \param[in] s scalar operand (right)
 * \return Replaces A with element-wise product A*s and returns the result.
 */
inline MATRIX3 &operator*= (MATRIX3 &A, double s)
{
	for (int i = 0; i < 9; i++) A.data[i] *= s;
	return A;
}

/**
 * \ingroup vec
 * \brief Matrix-scalar division-assignment A /= s
 * \param[in] A Matrix operand (left)
 * \param[in] s scalar operand (right)
 * \return Replaces A with element-wise quotient A/s and returns the result.
 * \note s != 0 is required.
 */
inline MATRIX3 &operator/= (MATRIX3 &A, double s)
{
	for (int i = 0; i < 9; i++) A.data[i] /= s;
	return A;
}

/**
 * \ingroup vec
 * \brief Matrix-vector multiplication
 * \param[in] A matrix operand
 * \param[in] b vector operand
 * \return Result of <b>Ab</b>
 */
inline VECTOR3 mul (const MATRIX3 &A, const VECTOR3 &b)
{
	return _V (
		A.m11*b.x + A.m12*b.y + A.m13*b.z,
		A.m21*b.x + A.m22*b.y + A.m23*b.z,
		A.m31*b.x + A.m32*b.y + A.m33*b.z);
}

/**
 * \ingroup vec
 * \brief Matrix transpose-vector multiplication
 * \param[in] A matrix operand
 * \param[in] b vector operand
 * \return Result of <b>A</b><sup>T</sup><b>b</b>
 */
inline VECTOR3 tmul (const MATRIX3 &A, const VECTOR3 &b)
{
	return _V (
		A.m11*b.x + A.m21*b.y + A.m31*b.z,
		A.m12*b.x + A.m22*b.y + A.m32*b.z,
		A.m13*b.x + A.m23*b.y + A.m33*b.z);
}

/**
 * \ingroup vec
 * \brief Matrix-matrix multiplication
 * \param[in] A First matrix operand
 * \param[in] B Second matrix operand
 * \return Result of <b>AB</b>
 */
inline MATRIX3 mul (const MATRIX3 &A, const MATRIX3 &B)
{
	MATRIX3 mat = {
		A.m11*B.m11 + A.m12*B.m21 + A.m13*B.m31, A.m11*B.m12 + A.m12*B.m22 + A.m13*B.m32, A.m11*B.m13 + A.m12*B.m23 + A.m13*B.m33,
		A.m21*B.m11 + A.m22*B.m21 + A.m23*B.m31, A.m21*B.m12 + A.m22*B.m22 + A.m23*B.m32, A.m21*B.m13 + A.m22*B.m23 + A.m23*B.m33,
		A.m31*B.m11 + A.m32*B.m21 + A.m33*B.m31, A.m31*B.m12 + A.m32*B.m22 + A.m33*B.m32, A.m31*B.m13 + A.m32*B.m23 + A.m33*B.m33
	};
	return mat;
}

/**
 * \ingroup vec
 * \brief Construct a rotation matrix from an axis and an angle
 * \param axis rotation axis direction (must be normalised)
 * \param angle rotation angle [rad]
 * \return rotation matrix
 */
inline MATRIX3 rotm (const VECTOR3 &axis, double angle)
{
	double c = cos(angle), s = sin(angle);
	double t = 1-c, x = axis.x, y = axis.y, z = axis.z;

	return _M(t*x*x+c, t*x*y-z*s, t*x*z+y*s,
		      t*x*y+z*s, t*y*y+c, t*y*z-x*s,
			  t*x*z-y*s, t*y*z+x*s, t*z*z+c);
}

inline VECTOR4 _V(double x, double y, double z, double w)
{
	VECTOR4 vec = {x,y,z,w}; return vec;
}

inline VECTOR4 _V(const VECTOR3 &v)
{
	VECTOR4 vec = {v.x, v.y, v.z, 1.0};
	return vec;
}

inline VECTOR4 mul (const MATRIX4 &A, const VECTOR4 &b)
{
	return _V (
		A.m11*b.x + A.m12*b.y + A.m13*b.z + A.m14*b.w,
		A.m21*b.x + A.m22*b.y + A.m23*b.z + A.m24*b.w,
		A.m31*b.x + A.m32*b.y + A.m33*b.z + A.m34*b.w,
		A.m41*b.x + A.m42*b.y + A.m43*b.z + A.m44*b.w);
}

inline VECTOR4 mul (const VECTOR4 &b, const MATRIX4 &A)
{
	return _V (
		b.x*A.m11 + b.y*A.m21 + b.z*A.m31 + b.w*A.m41,
		b.x*A.m12 + b.y*A.m22 + b.z*A.m32 + b.w*A.m42,
		b.x*A.m13 + b.y*A.m23 + b.z*A.m33 + b.w*A.m43,
		b.x*A.m14 + b.y*A.m24 + b.z*A.m34 + b.w*A.m44);
}

inline MATRIX4 _M(double m11, double m12, double m13, double m14,
				  double m21, double m22, double m23, double m24,
				  double m31, double m32, double m33, double m34,
				  double m41, double m42, double m43, double m44)
{
	MATRIX4 mat = {m11,m12,m13,m14,  m21,m22,m23,m24,  m31,m32,m33,m34, m41,m42,m43,m44};
	return mat;
}

/**
 * \ingroup vec
 * \brief Returns the identity matrix
 */
inline MATRIX4 identity4 ()
{
	static MATRIX4 mat = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
	return mat;
}

/**
 * \ingroup vec
 * \brief Matrix-matrix multiplication for 4-matrices
 * \param[in] A First matrix operand
 * \param[in] B Second matrix operand
 * \return Result of <b>AB</b>
 */
inline MATRIX4 mul (const MATRIX4 &A, const MATRIX4 &B)
{
	MATRIX4 mat = {
		A.m11*B.m11 + A.m12*B.m21 + A.m13*B.m31 + A.m14*B.m41, A.m11*B.m12 + A.m12*B.m22 + A.m13*B.m32 + A.m14*B.m42, A.m11*B.m13 + A.m12*B.m23 + A.m13*B.m33 + A.m14*B.m43, A.m11*B.m14 + A.m12*B.m24 + A.m13*B.m34 + A.m14*B.m44,
		A.m21*B.m11 + A.m22*B.m21 + A.m23*B.m31 + A.m24*B.m41, A.m21*B.m12 + A.m22*B.m22 + A.m23*B.m32 + A.m24*B.m42, A.m21*B.m13 + A.m22*B.m23 + A.m23*B.m33 + A.m24*B.m43, A.m21*B.m14 + A.m22*B.m24 + A.m23*B.m34 + A.m24*B.m44,
		A.m31*B.m11 + A.m32*B.m21 + A.m33*B.m31 + A.m34*B.m41, A.m31*B.m12 + A.m32*B.m22 + A.m33*B.m32 + A.m34*B.m42, A.m31*B.m13 + A.m32*B.m23 + A.m33*B.m33 + A.m34*B.m43, A.m31*B.m14 + A.m32*B.m24 + A.m33*B.m34 + A.m34*B.m44,
		A.m41*B.m11 + A.m42*B.m21 + A.m43*B.m31 + A.m44*B.m41, A.m41*B.m12 + A.m42*B.m22 + A.m43*B.m32 + A.m44*B.m42, A.m41*B.m13 + A.m42*B.m23 + A.m43*B.m33 + A.m44*B.m43, A.m41*B.m14 + A.m42*B.m24 + A.m43*B.m34 + A.m44*B.m44
	};
	return mat;
}

#endif
