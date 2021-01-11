import requests
import json
#TODO://a lot
class GeoUtils():
    def __init__(self):
        super().__init__()
        
    def createRegionObject(self, city, state) -> None:
        i=0
        region = {
            "latitudeMin":39.625923,
            "longitudeMin":-105.036412,
            "latitudeMax":39.833554,
            "longitudeMax":-104.731846
        }
        
        #get regional/city bbox coordinates from OSM
        r = requests.get('https://nominatim.openstreetmap.org/search?q=' + city + ' ' + state + '&format=geojson')
        data = json.loads(r.text)
        
        if data:
            #just take first one, no sense in getting precise
            lst = data['features'][0]['bbox']

            for key in region: 
                region[key]= lst[i]
                i=i+1

        return region


    def createPlaceObject(self,city, state) -> None:
        place = {
            "latitude":0,
            "longitude":0,
        }
        
        #get regional/city bbox coordinates from OSM
        r = requests.get('https://nominatim.openstreetmap.org/search?q=' + city + ' ' + state + '&format=json')
        data = json.loads(r.text)
        if data:
            #just take first one, no sense in getting precise
            place["latitude"] = data[0]["lat"]
            place["longitude"] = data[0]["lon"]

        return place

