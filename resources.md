# Resources

## Mapping
- OpenStreetMap: https://www.openstreetmap.org/
- Overpass Turbo: https://overpass-turbo.eu/
- Street lamps: https://wiki.openstreetmap.org/wiki/Tag:highway=street_lamp
- Lighting tag: https://wiki.openstreetmap.org/wiki/Key:lit

OSM supports `highway=street_lamp` and `lit=*`. These describe mapped infrastructure/lighting, not guaranteed current functionality.

## Routing
- OSRM: https://project-osrm.org/
- OSRM GitHub: https://github.com/Project-OSRM/osrm-backend
- OSRM docs: https://project-osrm.org/docs/

## Indian/open data
- Government OGD: https://data.gov.in/
- Smart Cities Open Data: https://smartcities.data.gov.in/
- IUDX: https://iudx.org.in/
- IUDX catalogue: https://central-catalogue.iudx.org.in/

Data availability varies by city/provider. An updated catalogue page does not mean the underlying observation is current.

## Existing research/products
- My Safetipin: https://safetipin.com/my-safetipin-app/
- Safetipin methodology: https://safetipin.com/methodology/
- SafeRoute: https://arxiv.org/abs/1811.01147
- Crowd-enabled safe route planning: https://arxiv.org/abs/2112.13760
- Road-safety ML: https://arxiv.org/abs/2006.03196

## Data rule
Every observation must contain:
source, timestamp, spatial scope, observation type, value, confidence, source reliability, verification state and freshness/decay policy.

Never store only `streetlight_working=true`.

## Current-data strategy
Historical data trains the predictive model. Current observations modify inference:
historical model + latest reports + current weather + latest infrastructure evidence + freshness + confidence.

## Important
Do not scrape private location data. Do not expose individual reporters. Do not claim a route is “safe” or “100% safe”.
