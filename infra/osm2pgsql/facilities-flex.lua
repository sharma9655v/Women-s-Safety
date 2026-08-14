-- osm2pgsql flex output: safety-relevant nodes -> facilities
-- Run with:
--   osm2pgsql -d mapforwomen -U postgres -H <host> -O flex \
--     infra/osm2pgsql/facilities-flex.lua data/<extract>.osm.pbf
-- Output schema must match apps/api/app/db/schema.sql.
--
-- API compatibility: osm2pgsql 2.x exposes the API as a loadable module
-- (require("osm2pgsql")), 1.x exposes it as a global table. Support both.

local ok, osm2pgsql = pcall(require, "osm2pgsql")
if not ok then
    osm2pgsql = _G.osm2pgsql
end

local facilities = osm2pgsql.define_table({
    name = "facilities",
    ids = { type = "node", id_column = "osm_id" },
    columns = {
        { column = "type", type = "text" },
        { column = "name", type = "text" },
        { column = "geometry", type = "point", projection = 4326 },
        { column = "operational_status", type = "text" },
        { column = "dataset_version", type = "text" },
    },
})

local TAG_TO_TYPE = {
    ["amenity=police"] = "police",
    ["amenity=hospital"] = "hospital",
    ["amenity=pharmacy"] = "pharmacy",
    ["amenity=fire_station"] = "fire_station",
    ["highway=bus_stop"] = "transit_stop",
    ["railway=station"] = "transit_stop",
    ["railway=tram_stop"] = "transit_stop",
    ["amenity=community_centre"] = "public_place",
    ["leisure=park"] = "public_place",
}

function osm2pgsql.process_node(object)
    local facility_type
    for tag, value in pairs(TAG_TO_TYPE) do
        local key, expected = tag:match("^([^=]+)=(.*)$")
        if object.tags[key] == expected then
            facility_type = value
            break
        end
    end
    if not facility_type then
        return
    end
    facilities:insert({
        osm_id = object.id,
        type = facility_type,
        name = object.tags.name,
        geometry = object:as_point(),
        operational_status = object.tags.disused and "disused" or "operational",
        dataset_version = object.tags.dataset_version or "unknown",
    })
end