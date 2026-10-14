// Independently authored minimal stdin/stdout adapter for externally pinned
// RoutingKit library. No vendor code is vendored into DriveMate Navigation.
#include <routingkit/contraction_hierarchy.h>
#include <vector>
#include <iostream>
#include <limits>
using namespace RoutingKit;
int main(){
    unsigned n,m,s,t;
    if(!(std::cin>>n>>m>>s>>t)||n<2||n>50000||m>1000000||s>=n||t>=n)return 2;
    std::vector<unsigned> tail,head,weight;
    tail.reserve(m);head.reserve(m);weight.reserve(m);
    for(unsigned i=0;i<m;++i){
        unsigned a,b,c;
        if(!(std::cin>>a>>b>>c)||a>=n||b>=n||c==0||c>100000000)return 3;
        tail.push_back(a);head.push_back(b);weight.push_back(c);
    }
    auto ch=ContractionHierarchy::build(n,tail,head,weight);
    ContractionHierarchyQuery query(ch);
    query.reset().add_source(s).add_target(t).run();
    if(query.get_distance()==std::numeric_limits<unsigned>::max()){
        std::cout<<"UNREACHABLE\n";
    }else{
        auto arcs=query.get_arc_path();
        std::cout<<"PATH";
        for(auto arc:arcs)std::cout<<" "<<arc;
        std::cout<<"\n";
    }
    return 0;
}
