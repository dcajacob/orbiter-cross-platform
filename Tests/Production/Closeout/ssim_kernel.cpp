// Licensed under the MIT License
// The retained Python image_ssim arithmetic, in the same scalar operation order.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>

template<class T> bool read(T* p,std::size_t n) {
    return bool(std::cin.read(reinterpret_cast<char*>(p),std::streamsize(n*sizeof(T))));
}
int main() {
    std::uint32_t width,height;
    std::array<double,13> parameters;
    if(!read(&width,1)||!read(&height,1)||width<11||height<11||
       width>16384||height>16384||!read(parameters.data(),parameters.size()))return 2;
    const std::size_t size=std::size_t(width)*height;
    std::vector<std::uint8_t> left(size*4),right(size*4);
    if(!read(left.data(),left.size())||!read(right.data(),right.size())||
       std::cin.peek()!=std::char_traits<char>::eof())return 2;
    double score=0.;std::uint64_t samples=0;
    const double c1=parameters[11],c2=parameters[12];
    for(unsigned channel=0;channel<3;++channel) {
        std::array<std::vector<double>,5> planes;
        for(auto& plane:planes)plane.resize(size,0.);
        for(unsigned y=0;y<height;++y)for(unsigned x=5;x<width-5;++x) {
            const std::size_t p=std::size_t(y)*width+x;
            std::array<double,5> values{};
            for(unsigned dx=0;dx<11;++dx) {
                const auto q=(p+dx-5)*4+channel;
                const double av=left[q],bv=right[q],w=parameters[dx];
                values[0]+=w*av;values[1]+=w*bv;
                values[2]+=w*av*av;values[3]+=w*bv*bv;values[4]+=w*av*bv;
            }
            for(unsigned i=0;i<5;++i)planes[i][p]=values[i];
        }
        for(unsigned y=5;y<height-5;++y)for(unsigned x=5;x<width-5;++x) {
            const std::size_t p=std::size_t(y)*width+x;
            std::array<double,5> values{};
            for(unsigned dy=0;dy<11;++dy) {
                const std::size_t q=p+(std::ptrdiff_t(dy)-5)*width;
                const double w=parameters[dy];
                for(unsigned i=0;i<5;++i)values[i]+=w*planes[i][q];
            }
            const double u=values[0],v=values[1],aa=values[2],bb=values[3],ab=values[4];
            const double va=std::max(0.,aa-u*u),vb=std::max(0.,bb-v*v),cov=ab-u*v;
            score+=((2*u*v+c1)*(2*cov+c2))/((u*u+v*v+c1)*(va+vb+c2));++samples;
        }
    }
    std::cout<<std::hexfloat<<score/samples<<'\n';
}
