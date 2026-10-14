#include "router.hpp"
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <locale>
#include <string>

template<class T> T read() {
    T value{};
    if(!(std::cin>>value)) throw std::invalid_argument("truncated/invalid input");
    return value;
}
template<> double read<double>() {
    std::string token=read<std::string>();char* end=nullptr;
    double value=std::strtod(token.c_str(),&end);
    if(end!=token.c_str()+token.size() || end==token.c_str() || !std::isfinite(value))
        throw std::invalid_argument("invalid floating point token");
    return value;
}
int count(int maximum) {
    int n=read<int>();
    if(n<0 || n>maximum) throw std::invalid_argument("count exceeds schema bounds");
    return n;
}
int main(int argc, char** argv) {
    try {
        const bool streaming = argc == 2 && std::string(argv[1]) == "--stream";
        if(argc > 2 || (argc == 2 && !streaming))
            throw std::invalid_argument("unsupported router mode");
        std::cin.imbue(std::locale::classic());std::cout.imbue(std::locale::classic());
        if(read<std::string>()!="DMNAV1") throw std::invalid_argument("unknown schema");
        int nn=count(200000),ne=count(1000000),nr=count(1000000),nt=count(1000000);
        std::vector<dm::Node> nodes;std::vector<dm::EdgeInput> edges;
        std::vector<dm::RuleInput> rules;std::vector<dm::TurnInput> turns;
        for(int i=0;i<nn;++i) nodes.push_back({read<dm::ID>(),read<double>(),read<double>()});
        for(int i=0;i<ne;++i) edges.push_back({read<dm::ID>(),read<dm::ID>(),read<dm::ID>(),
            read<dm::Cost>(),read<int>(),read<double>(),read<double>()});
        for(int i=0;i<nr;++i) {
            auto kind=read<std::string>();int mask=read<int>(),length=count(64);
            if(kind!="no" && kind!="only") throw std::invalid_argument("unknown rule type");
            std::vector<dm::ID> ids;for(int j=0;j<length;++j) ids.push_back(read<dm::ID>());
            rules.push_back({kind=="only",mask,std::move(ids)});
        }
        for(int i=0;i<nt;++i) turns.push_back({read<dm::ID>(),read<dm::ID>(),read<dm::Cost>()});
        int nl=count(64);std::vector<dm::ID> landmarks;
        for(int i=0;i<nl;++i) landmarks.push_back(read<dm::ID>());
        auto before=std::chrono::steady_clock::now();
        const dm::Router router(nodes,edges,rules,turns,landmarks);
        auto prep=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-before).count();
        std::cout<<"READY "<<prep<<"\n";
        if(streaming) std::cout.flush();
        int nq=count(1000000);
        if(streaming && nq != 0)
            throw std::invalid_argument("stream initial query count must be zero");
        auto query = [&](const std::string& name) {
            int mode=name=="dijkstra"?0:name=="astar"?1:name=="alt"?2:-1;
            auto a=read<dm::ID>(),b=read<dm::ID>();dm::Vehicle v{read<int>(),read<double>(),read<double>()};
            int nh=count(1000000);std::vector<dm::ID> history;
            for(int j=0;j<nh;++j) history.push_back(read<dm::ID>());
            before=std::chrono::steady_clock::now();
            auto result=router.route(a,b,v,mode,history);
            auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-before).count();
            if(result) {
                std::cout<<"FOUND "<<result->cost<<" "<<result->expanded<<" "<<ns<<" "<<result->edges.size();
                for(auto id:result->edges) std::cout<<" "<<id;
                std::cout<<"\n";
            } else std::cout<<"NONE "<<ns<<"\n";
            if(streaming) std::cout.flush();
        };
        if(streaming) {
            std::string name;
            while(std::cin >> name) query(name);
        } else {
            for(int i=0;i<nq;++i) query(read<std::string>());
            std::string extra;if(std::cin>>extra)
                throw std::invalid_argument("unexpected trailing input");
        }
        return 0;
    } catch(const std::exception& e) { std::cerr<<"ERROR "<<e.what()<<"\n";return 2; }
}
