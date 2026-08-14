-- osm2pgsql flex output: roads -> road_segments
-- Run with:
--   osm2pgsql -d mapforwomen -U postgres -H <host> -O flex \
--     infra/osm2pgsql/roads-flex.lua data/<extract>.osm.pbf
-- Output schema must match apps/api/app/db/schema.sql.
--
-- API compatibility: osm2pgsql 2.x exposes the API as a loadable module
-- (require("osm2pgsql")), 1.x exposes it as a global table. Support both.

local ok, osm2pgsql = pcall(require, "osm2pgsql")
if not ok then
    osm2pgsql = _G.osm2pgsql
end

local roads = osm2pgsql.define_table({
    name = "road_segments",
    ids = { type = "way", id_column = "osm_way_id" },
    columns = {
        { column = "geometry", type = "linestring", projection = 4326 },
        { column = "road_type", type = "text" },
        { column = "lit", type = "text" },
        { column = "data_source", type = "text" },
        { column = "dataset_version", type = "text" },
    },
})

-- Walkable/drivable highways; exclude proposed/construction and non-road
-- highway values (footway etc. are kept: safety evidence applies to them too).
local EXCLUDED_HIGHWAY = {
    ["proposed"] = true,
    ["construction"] = true,
    ["raceway"] = true,
    ["escape"] = true,
    ["bus_guideway"] = true,
}

function osm2pgsql.process_way(object)
    local highway = object.tags.highway
    if not highway or EXCLUDED_HIGHWAY[highway] then
        return
    end
    local geometry = object:as_linestring()
    if geometry then
        roads:insert({
            osm_way_id = object.id,
            geometry = geometry,
            road_type = highway,
            lit = object.tags.lit,
            data_source = "osm",
            dataset_version = object.tags.dataset_version or "unknown",
        })
    end
end