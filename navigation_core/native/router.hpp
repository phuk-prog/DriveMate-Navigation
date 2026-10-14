#pragma once
// Original DriveMate static routing research core. No third-party code/data.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <map>
#include <optional>
#include <queue>
#include <set>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

namespace dm {
using ID = std::int64_t;
using Cost = std::int64_t;
constexpr Cost INF = std::numeric_limits<Cost>::max();
constexpr Cost MAX_EDGE_COST = (Cost{1} << 53) - 1;
struct Node { ID id; double x, y; };
struct EdgeInput { ID id, u, v; Cost cost; int mask; double height, weight; };
struct RuleInput { bool only; int mask; std::vector<ID> ids; };
struct TurnInput { ID a, b; Cost cost; };
struct Vehicle { int kind; double height, weight; };
struct Edge { ID id; int u, v; Cost cost; int mask; double height, weight; };
struct State {
    int node, incoming, prefix;
    bool operator==(const State& other) const {
        return node==other.node && incoming==other.incoming && prefix==other.prefix;
    }
};
struct StateHash {
    std::size_t operator()(const State& s) const {
        std::size_t h=std::hash<int>{}(s.node);
        h ^= std::hash<int>{}(s.incoming) + 0x9e3779b9U + (h<<6) + (h>>2);
        h ^= std::hash<int>{}(s.prefix) + 0x9e3779b9U + (h<<6) + (h>>2);
        return h;
    }
};
struct Result { Cost cost; std::size_t expanded; std::vector<ID> edges; };
struct Action { std::set<int> forbidden, required; };

inline Cost add(Cost a, Cost b) {
    if (a<0 || b<0 || a>=INF-b) throw std::overflow_error("route cost capacity exceeded");
    return a+b;
}
inline void cost_valid(Cost c) {
    if(c<0 || c>MAX_EDGE_COST) throw std::invalid_argument("invalid integer edge/turn cost");
}
inline void dim_valid(double d) {
    if(!std::isfinite(d) || (d<0 && d!=-1)) throw std::invalid_argument("invalid dimension");
}
inline void mask_valid(int mask) {
    if(mask<0 || mask>3) throw std::invalid_argument("unsupported vehicle mask");
}

class Router {
    std::vector<Node> nodes_;
    std::vector<Edge> edges_;
    std::unordered_map<ID,int> node_ids_,edge_ids_;
    std::vector<std::vector<int>> out_, reverse_;
    std::map<std::pair<int,int>,Cost> turns_;
    std::map<std::vector<int>,int> prefix_ids_;
    std::vector<std::vector<int>> prefixes_;
    std::vector<std::array<Action,2>> actions_;
    int max_prefix_=0;
    long double scale_=0;
    std::vector<std::pair<std::vector<Cost>,std::vector<Cost>>> landmarks_;

    int node_id(ID n) const {
        auto it=node_ids_.find(n);
        if(it==node_ids_.end()) throw std::invalid_argument("unknown node");
        return it->second;
    }
    int edge_id(ID e) const {
        auto it=edge_ids_.find(e);
        if(it==edge_ids_.end()) throw std::invalid_argument("unknown edge");
        return it->second;
    }
    std::vector<Cost> distances(int source, bool reverse) const {
        std::vector<Cost> d(nodes_.size(),INF);
        using Entry=std::pair<Cost,int>;
        std::priority_queue<Entry,std::vector<Entry>,std::greater<Entry>> q;
        d[static_cast<std::size_t>(source)]=0; q.emplace(0,source);
        while(!q.empty()) {
            auto [cost,n]=q.top();q.pop();
            if(cost!=d[static_cast<std::size_t>(n)]) continue;
            for(int ei:(reverse?reverse_:out_)[static_cast<std::size_t>(n)]) {
                const auto& e=edges_[static_cast<std::size_t>(ei)];
                int other=reverse?e.u:e.v;
                Cost next=add(cost,e.cost);
                if(next<d[static_cast<std::size_t>(other)]) {
                    d[static_cast<std::size_t>(other)]=next;q.emplace(next,other);
                }
            }
        }
        return d;
    }
    int prefix(const std::vector<int>& history) const {
        int limit=std::min(max_prefix_,static_cast<int>(history.size()));
        for(int n=limit;n>0;--n) {
            std::vector<int> suffix(history.end()-n,history.end());
            auto it=prefix_ids_.find(suffix);
            if(it!=prefix_ids_.end()) return it->second;
        }
        return 0;
    }
    int advance(int state, int edge, int kind) const {
        const auto& a=actions_[static_cast<std::size_t>(state)][static_cast<std::size_t>(kind)];
        if(a.forbidden.count(edge) || (!a.required.empty() &&
            (a.required.size()!=1 || !a.required.count(edge)))) return -1;
        auto h=prefixes_[static_cast<std::size_t>(state)];
        h.push_back(edge);
        return prefix(h);
    }
    Cost heuristic(int n, int target, int mode) const {
        if(mode==0) return 0;
        const auto& a=nodes_[static_cast<std::size_t>(n)];
        const auto& b=nodes_[static_cast<std::size_t>(target)];
        long double raw=std::hypotl(static_cast<long double>(a.x)-b.x,
                                   static_cast<long double>(a.y)-b.y)*scale_;
        Cost value=std::isfinite(raw) && raw<static_cast<long double>(INF) && raw>=0
            ? static_cast<Cost>(std::floor(raw)):0;
        if(mode==2) {
            for(const auto& [f,r]:landmarks_) {
                if(f[static_cast<std::size_t>(target)]!=INF && f[static_cast<std::size_t>(n)]!=INF)
                    value=std::max(value,f[static_cast<std::size_t>(target)]-f[static_cast<std::size_t>(n)]);
                if(r[static_cast<std::size_t>(n)]!=INF && r[static_cast<std::size_t>(target)]!=INF)
                    value=std::max(value,r[static_cast<std::size_t>(n)]-r[static_cast<std::size_t>(target)]);
            }
        }
        return value;
    }
public:
    Router(const std::vector<Node>& nodes,const std::vector<EdgeInput>& input,
           const std::vector<RuleInput>& rules,const std::vector<TurnInput>& turns,
           const std::vector<ID>& landmarks):nodes_(nodes) {
        for(std::size_t i=0;i<nodes_.size();++i) {
            const auto& n=nodes_[i];
            if(!std::isfinite(n.x) || !std::isfinite(n.y) || !node_ids_.emplace(n.id,static_cast<int>(i)).second)
                throw std::invalid_argument("invalid/duplicate node");
        }
        out_.resize(nodes_.size());reverse_.resize(nodes_.size());
        long double min_scale=std::numeric_limits<long double>::infinity();
        for(const auto& in:input) {
            cost_valid(in.cost);mask_valid(in.mask);dim_valid(in.height);dim_valid(in.weight);
            int u=node_id(in.u),v=node_id(in.v),index=static_cast<int>(edges_.size());
            if(!edge_ids_.emplace(in.id,index).second) throw std::invalid_argument("duplicate edge");
            edges_.push_back({in.id,u,v,in.cost,in.mask,in.height,in.weight});
            out_[static_cast<std::size_t>(u)].push_back(index);
            reverse_[static_cast<std::size_t>(v)].push_back(index);
            const auto& a=nodes_[static_cast<std::size_t>(u)];
            const auto& b=nodes_[static_cast<std::size_t>(v)];
            long double length=std::hypotl(static_cast<long double>(a.x)-b.x,
                                           static_cast<long double>(a.y)-b.y);
            if(length>0) min_scale=std::min(min_scale,in.cost/length);
        }
        scale_=std::isfinite(min_scale)?min_scale*(1-1e-12L):0;
        for(const auto& t:turns) {
            cost_valid(t.cost);
            int a=edge_id(t.a),b=edge_id(t.b);
            if(edges_[static_cast<std::size_t>(a)].v!=edges_[static_cast<std::size_t>(b)].u ||
               !turns_.emplace(std::make_pair(a,b),t.cost).second)
                throw std::invalid_argument("invalid/duplicate turn");
        }
        prefixes_.push_back({});prefix_ids_[{}]=0;
        std::map<std::vector<int>,std::array<Action,2>> direct;
        for(const auto& r:rules) {
            mask_valid(r.mask);
            if(r.ids.size()<2) throw std::invalid_argument("short restriction");
            std::vector<int> seq;
            for(ID id:r.ids) seq.push_back(edge_id(id));
            for(std::size_t i=1;i<seq.size();++i)
                if(edges_[static_cast<std::size_t>(seq[i-1])].v!=edges_[static_cast<std::size_t>(seq[i])].u)
                    throw std::invalid_argument("disconnected restriction");
            for(std::size_t i=1;i<seq.size();++i) {
                std::vector<int> p(seq.begin(),seq.begin()+static_cast<std::ptrdiff_t>(i));
                if(!prefix_ids_.count(p)) {
                    prefix_ids_[p]=static_cast<int>(prefixes_.size());prefixes_.push_back(p);
                    max_prefix_=std::max(max_prefix_,static_cast<int>(i));
                }
                for(int kind=0;kind<2;++kind) if(r.mask&(1<<kind)) {
                    if(r.only) direct[p][static_cast<std::size_t>(kind)].required.insert(seq[i]);
                    else if(i==seq.size()-1) direct[p][static_cast<std::size_t>(kind)].forbidden.insert(seq[i]);
                }
            }
        }
        actions_.resize(prefixes_.size());
        for(std::size_t i=1;i<prefixes_.size();++i) {
            const auto& p=prefixes_[i];
            for(std::size_t j=0;j<p.size();++j) {
                std::vector<int> suffix(p.begin()+static_cast<std::ptrdiff_t>(j),p.end());
                auto it=direct.find(suffix);
                if(it==direct.end()) continue;
                for(std::size_t kind=0;kind<2;++kind) {
                    const auto& a=it->second[kind];auto& to=actions_[i][kind];
                    to.forbidden.insert(a.forbidden.begin(),a.forbidden.end());
                    to.required.insert(a.required.begin(),a.required.end());
                }
            }
        }
        std::set<ID> seen;
        for(ID n:landmarks) if(seen.insert(n).second) {
            int source=node_id(n);landmarks_.emplace_back(distances(source,false),distances(source,true));
        }
    }

    std::optional<Result> route(ID origin,ID destination,Vehicle vehicle,int mode,
                                const std::vector<ID>& inbound) const {
        if(mode<0 || mode>2 || vehicle.kind<0 || vehicle.kind>1)
            throw std::invalid_argument("unknown mode/vehicle");
        dim_valid(vehicle.height);dim_valid(vehicle.weight);
        int start=node_id(origin),target=node_id(destination);
        std::vector<int> history;
        for(ID id:inbound) history.push_back(edge_id(id));
        for(std::size_t i=1;i<history.size();++i)
            if(edges_[static_cast<std::size_t>(history[i-1])].v!=edges_[static_cast<std::size_t>(history[i])].u)
                throw std::invalid_argument("disconnected history");
        if(!history.empty() && edges_[static_cast<std::size_t>(history.back())].v!=start)
            throw std::invalid_argument("history ends at wrong node");
        State initial{start,history.empty()?-1:history.back(),prefix(history)};
        struct Entry { Cost estimate,cost;std::uint64_t serial;State state; };
        struct Later {
            bool operator()(const Entry& a,const Entry& b) const {
                return std::tie(a.estimate,a.cost,a.serial)>std::tie(b.estimate,b.cost,b.serial);
            }
        };
        struct Parent { State previous; int edge; };
        std::unordered_map<State,Cost,StateHash> best;
        std::unordered_map<State,Parent,StateHash> parents;
        std::priority_queue<Entry,std::vector<Entry>,Later> queue;
        best[initial]=0;queue.push({heuristic(start,target,mode),0,0,initial});
        std::uint64_t serial=1;std::size_t expanded=0;
        while(!queue.empty()) {
            auto current=queue.top();queue.pop();const auto& state=current.state;
            if(current.cost!=best.at(state)) continue;
            ++expanded;
            if(state.node==target) {
                std::vector<ID> path;State s=state;
                while(!(s==initial)) {
                    const auto& p=parents.at(s);path.push_back(edges_[static_cast<std::size_t>(p.edge)].id);s=p.previous;
                }
                std::reverse(path.begin(),path.end());return Result{current.cost,expanded,std::move(path)};
            }
            for(int ei:out_[static_cast<std::size_t>(state.node)]) {
                const auto& e=edges_[static_cast<std::size_t>(ei)];
                if(!(e.mask&(1<<vehicle.kind)) ||
                   (e.height!=-1 && (vehicle.height==-1 || vehicle.height>e.height)) ||
                   (e.weight!=-1 && (vehicle.weight==-1 || vehicle.weight>e.weight))) continue;
                int next_prefix=advance(state.prefix,ei,vehicle.kind);
                if(next_prefix<0) continue;
                State next{e.v,ei,next_prefix};
                Cost total=add(current.cost,e.cost);
                auto turn=turns_.find({state.incoming,ei});
                if(turn!=turns_.end()) total=add(total,turn->second);
                auto old=best.find(next);
                if(old==best.end() || total<old->second) {
                    best[next]=total;parents[next]={state,ei};
                    queue.push({add(total,heuristic(e.v,target,mode)),total,serial++,next});
                }
            }
        }
        return std::nullopt;
    }
};
} // namespace dm
