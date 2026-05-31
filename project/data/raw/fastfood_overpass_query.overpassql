[out:json][timeout:180];
area["ISO3166-1"="AU"][admin_level=2]->.australia;
(
  node["amenity"="fast_food"](area.australia);
  way["amenity"="fast_food"](area.australia);
  relation["amenity"="fast_food"](area.australia);
);
out center tags;
