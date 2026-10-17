"""Research-only verified map activation in memory, with no networking or disk IO.

A caller-trusted manifest binds bytes/coverage, not source authenticity or map
freshness. This is not an Android/native package installer or crash-safe store.
"""
from dataclasses import dataclass
from hashlib import sha256
import re
from engine import Route, shortest_route
from .osm_xml import JourneyAccessContext, OSMImportError, Provenance, import_osm_xml

# Device offline-package payload limit (unchanged 6 MB contract), separate from the
# research importer limit used for real-road clips.
MAX_INPUT_BYTES = 6_000_000


class PackageValidationError(ValueError):
    """Incoming package cannot replace the current verified map."""


class NoActiveMap(ValueError):
    """No verified map has been activated."""


class CoverageUnavailable(ValueError):
    """Requested node is not present; this is not a no-legal-route result."""


@dataclass(frozen=True)
class PackageInfo:
    sha256: str
    region: str
    snapshot: str
    required_nodes: tuple[str,...]
    vertices: int
    edges: int


@dataclass(frozen=True)
class OfflineRoute:
    package_sha256: str
    route: Route


class OfflineMapStore:
    def __init__(self,*,max_payload_bytes=MAX_INPUT_BYTES,allow_conditional=True):
        if type(max_payload_bytes) is not int or not 1<=max_payload_bytes<=MAX_INPUT_BYTES:
            raise ValueError('Invalid offline package size limit')
        if type(allow_conditional) is not bool:
            raise ValueError('Invalid allow_conditional')
        # False = the original strict device contract (frozen OFFLINE-001 trial only)
        self._allow_conditional=allow_conditional
        self._limit=max_payload_bytes
        self._active=None

    @property
    def info(self):
        return self._active[0] if self._active is not None else None

    def activate(self,payload,manifest):
        # Stage all checks and parsing in local variables; publish one pointer only
        # after success. No failed validation mutates the prior active snapshot.
        if type(payload) is not bytes or not 0<len(payload)<=self._limit:
            raise PackageValidationError('Nonempty immutable bytes within size limit required')
        keys={'schema_version','format','byte_length','sha256','provenance','required_nodes'}
        if type(manifest) is not dict or set(manifest)!=keys:
            raise PackageValidationError('Exact manifest schema required')
        if type(manifest['schema_version']) is not int or manifest['schema_version']!=1 or manifest['format']!='dmn-osm-xml-v1':
            raise PackageValidationError('Unsupported schema or format')
        if type(manifest['byte_length']) is not int or manifest['byte_length']!=len(payload):
            raise PackageValidationError('Byte length mismatch')
        digest=manifest['sha256']
        if type(digest) is not str or re.fullmatch('[0-9a-f]{64}',digest) is None or sha256(payload).hexdigest()!=digest:
            raise PackageValidationError('SHA256 mismatch')
        provenance=manifest['provenance']
        if (type(provenance) is not dict or set(provenance)!={'region','snapshot','source','attribution'}
                or any(type(v) is not str or not 1<=len(v)<=512 for v in provenance.values())):
            raise PackageValidationError('Complete bounded provenance required')
        anchors=manifest['required_nodes']
        if (type(anchors) is not list or not 1<=len(anchors)<=32
                or any(type(n) is not str or re.fullmatch(r'osm:[1-9][0-9]{0,18}',n) is None for n in anchors)
                or len(set(anchors))!=len(anchors)):
            raise PackageValidationError('Explicit unique coverage anchors required')
        # Time-limited (:conditional) rules no longer reject the package (owner-approved,
        # 17 Oct 2026; run D found 2 of 3 real UK clips refused). The importer handles them
        # per road: in force at all times unless route() is given the current time.
        if not self._allow_conditional and re.search(rb'<tag\s+k="[^"]*:conditional"',payload):
            raise PackageValidationError('Map validation failed: conditional tags are unsupported in offline packages')
        try:data=import_osm_xml(payload,provenance=Provenance(**provenance))
        except OSMImportError as exc:raise PackageValidationError(str(exc)) from exc
        if not set(anchors)<=data.graph.vertices:
            raise PackageValidationError('Required node coverage missing')
        info=PackageInfo(digest,provenance['region'],provenance['snapshot'],tuple(anchors),len(data.graph.vertices),len(data.graph.edges))
        self._active=(info,data,payload)
        return info

    def route(self,source,destination,*,access_context=None,when=None):
        """`when` (UK local datetime, optional): time-limited rules apply only while in force."""
        active=self._active
        if active is None:raise NoActiveMap('No verified active map')
        info,data,payload=active
        if type(source) is not str or type(destination) is not str or source not in data.graph.vertices or destination not in data.graph.vertices:
            raise CoverageUnavailable('Requested node is not covered by active map')
        if when is not None and access_context is None:
            # Time view rebuilt in memory; the active package itself stays time-free.
            data=import_osm_xml(payload,provenance=Provenance(
                data.metadata['region'],data.metadata['snapshot'],data.metadata['source'],
                data.metadata['attribution']),when=when)
        if access_context is not None:
            if not isinstance(access_context,JourneyAccessContext):
                raise OSMImportError("Expected JourneyAccessContext")
            if access_context.destination_node is not None and access_context.destination_node != destination:
                raise ValueError('Access context belongs to another destination')
            # Journey view is rebuilt in memory; active package remains context-free.
            data=import_osm_xml(payload,provenance=Provenance(
                data.metadata['region'],data.metadata['snapshot'],data.metadata['source'],
                data.metadata['attribution']),access_context=access_context,when=when)
        route=shortest_route(data.graph,source,destination)
        return OfflineRoute(info.sha256,route)
