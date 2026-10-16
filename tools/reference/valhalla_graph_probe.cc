// Read-only graph metadata exporter. No Valhalla or DMN routing modification.
#include <valhalla/baldr/graphreader.h>
#include <valhalla/baldr/graphtile.h>
#include <valhalla/baldr/graphconstants.h>
#include <valhalla/midgard/logging.h>
#include <boost/property_tree/json_parser.hpp>
#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
  try {
    if (argc != 2) throw std::runtime_error("Expected one config path");
    boost::property_tree::ptree config;
    boost::property_tree::read_json(argv[1], config);
    valhalla::midgard::logging::Configure({{"type","std_err"},{"color","false"}});
    using namespace valhalla::baldr;
    GraphReader reader(config.get_child("mjolnir"));
    // Local road level only: avoid hierarchy duplicates and shortcut semantics.
    const auto tiles = reader.GetTileSet(2);
    if (tiles.empty() || tiles.size() > 100) throw std::runtime_error("Unexpected tile count");
    size_t count=0;
    for (const auto& tid : tiles) {
      auto tile=reader.GetGraphTile(tid);
      if (!tile) throw std::runtime_error("Enumerated tile unavailable");
      for (uint32_t ni=0; ni<tile->header()->nodecount(); ++ni) {
        GraphId source=tid; source.set_id(ni);
        const auto* node=tile->node(ni);
        for (uint32_t j=0; j<node->edge_count(); ++j) {
          const auto ei=node->edge_index()+j;
          const auto* edge=tile->directededge(ei);
          if (edge->is_shortcut() || edge->IsTransitLine()) continue;
          if (++count > 100000) throw std::runtime_error("Edge bound exceeded");
          GraphId id=tid; id.set_id(ei);
          auto info=tile->edgeinfo(edge);
          auto shape=info.shape();
          if (!edge->forward()) std::reverse(shape.begin(),shape.end());
          if (shape.size()>10000) throw std::runtime_error("Shape bound exceeded");
          std::cout << std::setprecision(9) << "{\"kind\":\"edge\",\"graph_id\":" << uint64_t(id)
                    << ",\"way_id\":" << info.wayid() << ",\"start_node\":" << uint64_t(source)
                    << ",\"end_node\":" << uint64_t(edge->endnode())
                    << ",\"car_access\":" << ((edge->forwardaccess() & kAutoAccess) ? "true":"false")
                    << ",\"restriction_mask\":" << edge->restrictions()
                    << ",\"local_index\":" << edge->localedgeidx()
                    << ",\"access_restriction\":" << edge->access_restriction()
                    << ",\"start_restriction\":" << edge->start_restriction()
                    << ",\"end_restriction\":" << edge->end_restriction()
                    << ",\"complex\":" << (edge->part_of_complex_restriction()?"true":"false")
                    << ",\"destination_only\":" << (edge->destonly()?"true":"false")
                    << ",\"shape\":[";
          bool first=true;
          for (const auto& pt : shape) {
            if (!first) std::cout << ',';
            first=false; std::cout << '[' << pt.lat() << ',' << pt.lng() << ']';
          }
          std::cout << "]}\n";
        }
      }
    }
    std::cout << "{\"kind\":\"complete\",\"local_tiles\":" << tiles.size()
              << ",\"directed_edges\":" << count << "}\n";
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "Native probe failed: " << e.what() << '\n';
    return 1;
  }
}
