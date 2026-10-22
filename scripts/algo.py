import json
from datetime import date, timedelta

dfile_path = r"Q:\CycleAlgo\Data\fosol_cycle_rajshahi_crop_dataset.json"
ifile_path = r"Q:\CycleAlgo\Data\fosol_cycle_rajshahi_crop_dataset.json"

with open(dfile_path,"r",encoding="utf-8") as file:
    crops = json.load(file)

with open(ifile_path, 'r', encoding='utf-8') as file:
    input = json.load(file)  


#1 Input Validator

def is_valid_iso_date(date_string):
    # Check if the string is empty or None first
    if not date_string:
        return False
        
    try:
        # Attempts to parse strictly ISO 8601 format (YYYY-MM-DD)
        date.fromisoformat(date_string)
        return True
    except ValueError:
        # Returns False if the format is wrong or the date doesn't exist (e.g., Feb 30)
        return False

def validateInput(input,crops):
    if "location" not in input or "current_crop" not in input or "field" not in input:
        print("Missing require core information")
        return False
    currentCrop = input["current_crop"]
    if currentCrop.get("crop_id") not in crops["crops"]:
        print("Invalid current crop ID")
        return False
    if not is_valid_iso_date(currentCrop.get("planting_date")):
        print("Invalid planting date format.")
        return False
    harvestDate=currentCrop.get("actual_harvest_date")
    if harvestDate is not None and not is_valid_iso_date(harvestDate):
        return False;
    
    nextCropBlock = input.get("next_crop") or {}
    nextCropid=nextCropBlock.get("crop_id")
    
    if nextCropid is not None:
        if nextCropid not in crops.get("crops"):
            print("Invalid next Crop ID")
            return False
        
    field = input.get("field")
    validIrrigation=["none","limited","adequate"]
    
    if field.get("irrigation","").lower() not in validIrrigation:
        print("Invalid Irrigation")
        return False
    soilPh=field.get("soil_ph")
    if soilPh is not None and not isinstance(soilPh, (int,float)):
        return False
    
    priorities = input.get("priorities") or {}
    for key, value in priorities.items():
        if value is not None:
            if not isinstance(value, int) or not (1 <= value <= 5):
                print(f"Priority {key} must be an integer between 1 and 5.")
                return False
            
    return True

def add_days(date_string, dayss):
    d =date.fromisoformat(date_string)
    new_d = d + timedelta(days=dayss)
    return new_d.isoformat()

def calculate_harvest_range(input, crops):
    current_crop = input["current_crop"]
    crop_id = current_crop["crop_id"]          # Grabs "aman_br11"
    crop_profile = crops["crops"][crop_id]     # Looks up crops["crops"]["aman_br11"]
    if current_crop.get("actual_harvest_date") is not None:
        actualDate= current_crop["actual_harvest_date"]
        return {
            "earliest": actualDate,
            "latest": actualDate
        }
    plantingDate = current_crop.get("planting_date")
    min_days = crop_profile["duration"]["variety"]["min_days"]
    max_days = crop_profile["duration"]["variety"]["max_days"]
    return{
        "earliest": add_days(plantingDate,min_days),
        "latest": add_days(plantingDate,max_days)
    }


def calculate_field_ready_range(harvest_range,turnaround_days):
    return{
        "earliest":add_days(harvest_range.get("earliest"),turnaround_days),
        "latest": add_days(harvest_range.get("latest"),turnaround_days)
    }
    ##some work needs to be done here as this has some risks
        