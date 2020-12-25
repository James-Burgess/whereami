import re


def process_spot(data):
    ords = re.findall(r'\b((?:Lat|Long)itude: [-]*\d+.\d+)', data)
    time = re.findall(r'(?:\d{2}/)+\d{4} (?:\d{2}:?)+', data)
    ret= {
        "lat": ords[0].split()[-1],
        "lng": ords[1].split()[-1],
        "time": time[0],
    }
    print(ret)
    return ret
