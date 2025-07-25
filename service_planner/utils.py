import frappe
import os
import json

def load_translations():
    """تحميل الترجمات من ملفات JSON"""
    app_path = frappe.get_app_path("service_planner")
    translations_path = os.path.join(app_path, "translations")
    
    if os.path.exists(translations_path):
        for filename in os.listdir(translations_path):
            if filename.endswith(".json"):
                lang = filename.replace(".json", "")
                file_path = os.path.join(translations_path, filename)
                
                with open(file_path, "r", encoding="utf-8") as f:
                    translations = json.load(f)
                    
                for key, value in translations.items():
                    frappe.local.lang_dict[lang][key] = value
