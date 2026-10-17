// Research adapter for actual Itinero; real public map, synthetic selected GPS
// endpoints, never personal traces. No standalone Android navigation app.
using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using Itinero;
using Itinero.IO.Osm;
using Itinero.LocalGeo;
using Itinero.Osm.Vehicles;

class Reference
{
    static void Main(string[] args)
    {
        if (args.Length != 3) throw new ArgumentException("map, requests, output required");
        var db = new RouterDb();
        using (var stream = File.OpenRead(args[0])) db.LoadOsmData(stream, Vehicle.Car);
        var profile = db.GetSupportedProfile("car");
        var router = new Router(db); // uncontracted; no fabricated result/fallback
        using var document = JsonDocument.Parse(File.ReadAllText(args[1]));
        var rows = document.RootElement.GetProperty("cases").EnumerateArray().Select(c =>
        {
            var id = c.GetProperty("id").GetString();
            var a = c.GetProperty("start"); var b = c.GetProperty("end");
            try
            {
                var route = router.Calculate(profile,
                    new Coordinate(a[0].GetSingle(), a[1].GetSingle()),
                    new Coordinate(b[0].GetSingle(), b[1].GetSingle()));
                return new { id, status = "OUTPUT", reason = "", points = route.Shape.Select(p => new double[] {p.Latitude,p.Longitude}).ToArray() };
            }
            catch (Exception e)
            {
                return new { id, status = "UNRESOLVED", reason = e.GetType().Name + ": " + e.Message, points = Array.Empty<double[]>() };
            }
        }).ToArray();
        File.WriteAllText(args[2], JsonSerializer.Serialize(new {
            classification = "real public OSM; synthetic selected GPS endpoints; actual routing only, not real GNSS or independent legality",
            assembly_version = typeof(Router).Assembly.GetName().Version.ToString(),
            profile = "car; uncontracted", cases = rows }));
    }
}
