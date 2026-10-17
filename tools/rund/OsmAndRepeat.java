// Run D speed (owner, 17 Oct 2026): OsmAnd's own Java router, timed warm in-process, as a yardstick.
// Loads the OBF once, routes once (warm-up), then N more times, each on a fresh routing context, and
// prints one JSON line: the route line, the N timings in ms and whether every line was the same.
// Usage: java -cp <OsmAndMapCreator.jar:lib/*:.> OsmAndRepeat <obf> <lat1> <lon1> <lat2> <lon2> <head1> <n>
import java.io.File;
import java.io.RandomAccessFile;
import java.util.ArrayList;
import java.util.List;

import net.osmand.binary.BinaryMapIndexReader;
import net.osmand.data.LatLon;
import net.osmand.router.RoutePlannerFrontEnd;
import net.osmand.router.RouteResultPreparation;
import net.osmand.router.RouteSegmentResult;
import net.osmand.router.RoutingConfiguration;

public class OsmAndRepeat {
    public static void main(String[] args) throws Exception {
        File obf = new File(args[0]);
        LatLon start = new LatLon(Double.parseDouble(args[1]), Double.parseDouble(args[2]));
        LatLon end = new LatLon(Double.parseDouble(args[3]), Double.parseDouble(args[4]));
        int repeat = Integer.parseInt(args[6]);
        BinaryMapIndexReader reader = new BinaryMapIndexReader(new RandomAccessFile(obf, "r"), obf);
        RoutingConfiguration config = RoutingConfiguration.getDefault()
                .build("car", new RoutingConfiguration.RoutingMemoryLimits(512, 256));
        config.initialDirection = Math.toRadians(Double.parseDouble(args[5]));  // as OsmAndRoute
        RoutePlannerFrontEnd fe = new RoutePlannerFrontEnd();
        BinaryMapIndexReader[] readers = {reader};
        String first = line(fe.searchRoute(fe.buildRoutingContext(config, null, readers), start, end, null));
        boolean same = true;
        List<String> times = new ArrayList<>();
        for (int k = 0; k < repeat; k++) {
            var ctx = fe.buildRoutingContext(config, null, readers);
            long t0 = System.nanoTime();
            RouteResultPreparation.RouteCalcResult res = fe.searchRoute(ctx, start, end, null);
            times.add(String.format("%.2f", (System.nanoTime() - t0) / 1e6));
            same &= line(res).equals(first);
        }
        String points = first.equals("null") ? "null" : "[" + first + "]";
        System.out.println("{\"points\":" + points + ",\"repeat_ms\":[" + String.join(",", times)
                + "],\"repeat_same\":" + same + "}");
    }

    private static String line(RouteResultPreparation.RouteCalcResult res) {
        if (res == null || !res.isCorrect() || res.getList().isEmpty()) return "null";
        List<String> pts = new ArrayList<>();
        for (RouteSegmentResult s : res.getList()) {
            int a = s.getStartPointIndex(), e = s.getEndPointIndex(), step = a <= e ? 1 : -1;
            for (int i = a; ; i += step) {
                LatLon p = s.getPoint(i);
                pts.add(String.format("[%.7f,%.7f]", p.getLatitude(), p.getLongitude()));
                if (i == e) break;
            }
        }
        return String.join(",", pts);
    }
}
