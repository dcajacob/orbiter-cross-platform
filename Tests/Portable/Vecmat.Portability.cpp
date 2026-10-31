// Licensed under the MIT License; exercises the existing Orbiter implementation.
#include "Vecmat.h"
#include <cmath>
#include <iostream>
#include <stdexcept>

void require(bool ok, const char *message) {
    if (!ok) throw std::runtime_error(message);
}
void close(double value, double expected) {
    require(std::isfinite(value) && std::abs(value-expected) <= 1e-12,
            "numerical result outside absolute tolerance 1e-12");
}
template<class M, class V> void solve(int n, bool default_argument) {
    M a;
    V c, d, rhs;
    // Well-conditioned dense system with known solution (1, 2, ..., n).
    for (int i=0; i<n; ++i) {
        rhs(i)=0;
        for (int j=0; j<n; ++j) {
            a(i,j) = i==j ? 5.0+i : 0.25;
            rhs(i) += a(i,j)*(j+1);
        }
    }
    int singular = -1;
    if (default_argument) qrdcmp(a,c,d);
    else {
        qrdcmp(a,c,d,&singular);
        require(singular==0, "nonsingular matrix marked singular");
    }
    qrsolv(a,c,d,rhs);
    for (int i=0; i<n; ++i) close(rhs(i),i+1);
    M zero;
    for (int i=0; i<n; ++i)
        for (int j=0; j<n; ++j) zero(i,j)=0;
    qrdcmp(zero,c,d,&singular);
    require(singular==1, "zero matrix not marked singular");
}
int main() {
    try {
        solve<Matrix,Vector>(3,false);
        solve<Matrix,Vector>(3,true);
        solve<Matrix4,Vector4>(4,false);
        solve<Matrix4,Vector4>(4,true);
        Vector v(3,4,0);
        close(v.length(),5);
        close(v.unit().length(),1);
        Vector result=mul(IMatrix(),v);
        close(result.x,3); close(result.y,4); close(result.z,0);
        std::cout << "PASS: 3x3/4x4 QR solves, default arguments, singular flags, vector normalization, identity transform\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
