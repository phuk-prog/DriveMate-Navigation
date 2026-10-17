# DMN geographic GPS cohort — conservative conditional-road exclusion

The bounded research importer deliberately rejects conditional road/turn
rules when the trial cannot prove current date/time/legal applicability.
The three-region GPS runner now **excludes entire affected ways and dependent
turn manoeuvres**, never just deletes a tag while keeping the edge. It records
counts of omitted ways, conditional nodes, unsupported turn relations and
dependencies, along with both unchanged raw-extract SHA and scored subset SHA.
The source archive, default DMN implementation and other test suites remain
unchanged.

Those excluded roads are explicitly **UNKNOWN/NOT_JUDGED**; a provisional
OSM-source correctness count on the remaining roads is not independent
verification of current UK road legality. No engine function has been disabled.
