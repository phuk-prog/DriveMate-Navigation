// OsmAnd yardstick for DMN research (owner, 17 Oct 2026): runs OsmAnd's own Java router on an
// OBF file built from the SAME OSM clip and prints one JSON line. Nothing from it feeds DriveMate.
// Usage: java -cp <OsmAndMapCreator.jar:lib/*:.> OsmAndRoute <obf> <lat1> <lon1> <lat2> <lon2> <head1> <head2>
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
import net.osmand.router.RoutingContext;
import net.osmand.router.TurnType;

public class OsmAndRoute {
    public static void main(String[] args) throws Exception {
        File obf = new File(args[0]);
        LatLon start = new LatLon(Double.parseDouble(args[1]), Double.parseDouble(args[2]));
        LatLon end = new LatLon(Double.parseDouble(args[3]), Double.parseDouble(args[4]));
        BinaryMapIndexReader reader = new BinaryMapIndexReader(new RandomAccessFile(obf, "r"), obf);
        RoutingConfiguration config = RoutingConfiguration.getDefault()
                .build("car", new RoutingConfiguration.RoutingMemoryLimits(512, 256));
        // same start/finish travel direction the other engines get (compass degrees -> radians)
        config.initialDirection = Math.toRadians(Double.parseDouble(args[5]));
        if (args.length > 7 && args[7].equals("target")) config.targetDirection = Math.toRadians(Double.parseDouble(args[6]));
        RoutePlannerFrontEnd fe = new RoutePlannerFrontEnd();
        RoutingContext ctx = fe.buildRoutingContext(config, null, new BinaryMapIndexReader[]{reader});
        long began = System.nanoTime();
        RouteResultPreparation.RouteCalcResult res = fe.searchRoute(ctx, start, end, null);
        double ms = (System.nanoTime() - began) / 1e6;
        StringBuilder out = new StringBuilder("{\"ms\":").append(String.format("%.1f", ms));
        if (res == null || !res.isCorrect() || res.getList().isEmpty()) {
            out.append(",\"route\":null}");
            System.out.println(out);
            return;
        }
        List<String> points = new ArrayList<>(), steps = new ArrayList<>(), limits = new ArrayList<>();
        for (RouteSegmentResult s : res.getList()) {
            int a = s.getStartPointIndex(), b = s.getEndPointIndex(), step = a <= b ? 1 : -1;
            int firstPoint = points.size();
            for (int i = a; ; i += step) {
                LatLon p = s.getPoint(i);
                points.add(String.format("[%.7f,%.7f]", p.getLatitude(), p.getLongitude()));
                if (i == b) break;
            }
            float speed = s.getObject().getMaximumSpeed(s.isForwardDirection());  // m/s, 0 when unknown
            for (int i = 0; i < Math.abs(b - a); i++) limits.add(speed > 0 ? String.format("%.2f", speed * 3.6) : "null");
            limits.add("null");  // the joint to the next segment carries no limit of its own
            TurnType t = s.getTurnType();
            if (t != null) {
                LatLon at = s.getStartPoint();
                StringBuilder lanes = new StringBuilder("[");
                int[] ln = t.getLanes();
                if (ln != null) {
                    for (int i = 0; i < ln.length; i++) {
                        if ((ln[i] & 1) == 1) lanes.append(lanes.length() > 1 ? "," : "").append(i + 1);
                    }
                }
                lanes.append("]");
                steps.add(String.format("{\"at\":[%.7f,%.7f],\"value\":%d,\"exit\":%d,\"roundabout\":%b,\"lanes\":%s,"
                        + "\"lane_count\":%d,\"point\":%d}", at.getLatitude(), at.getLongitude(), t.getValue(),
                        t.getExitOut(), t.isRoundAbout(), lanes, ln == null ? 0 : ln.length, firstPoint));
            }
        }
        if (!limits.isEmpty()) limits.remove(limits.size() - 1);
        out.append(",\"points\":[").append(String.join(",", points)).append("]");
        out.append(",\"limits_kph\":[").append(String.join(",", limits)).append("]");
        out.append(",\"steps\":[").append(String.join(",", steps)).append("]}");
        System.out.println(out);
    }
}
