from flask import Flask, render_template, request, redirect
import requests
from typing import List, Dict, Any, Set

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def welcome() -> str:
    if request.method == "POST":
        name: str = request.form.get("name")
        if name:
            return redirect(f"/pokemon/{name}")

    params: dict = request.args.to_dict()

    api_url: str = "https://pokeapi.co/api/v2/pokemon"

    response = requests.get(f"{api_url}")
    if response.status_code == 200:
        pokemon_data: List[Dict[str, Any]] = []
        page_data: Dict[str, Any] = response.json().get("results", [])
        for pokemon in page_data:
            pokemon_info: Dict[str, Any] = {}
            pokemon_info["name"] = pokemon["name"].capitalize()
            pokemon_info["url"] = pokemon["url"]
            pokemon_info["image"] = get_pokemon_image(pokemon["url"])
            pokemon_info["height"] = get_pokemon_height(pokemon["url"])
            pokemon_data.append(pokemon_info)

        if params:
            pokemons: List[Dict[str, Any]] = filter_pokemons(pokemon_data, params)
        else:
            pokemons: List[Dict[str, Any]] = pokemon_data
    else:
        pokemons = []

    return render_template("pokemons.html", pokemon_data=pokemons, params=params)


def get_pokemon_image(url: str) -> str:
    response = requests.get(url)
    if response.status_code == 200:
        data: Dict[str, Any] = response.json()
        if "sprites" in data and "front_default" in data["sprites"]:
            return data["sprites"]["front_default"]
    return ""

def get_pokemon_types(url: str) -> List[str]:
    response = requests.get(url)
    if response.status_code == 200:
        data: Dict[str, Any] = response.json()
        types: List[str] = [t["type"]["name"] for t in data.get("types", [])]
        return types
    return []

def get_type_weaknesses(type_name: str) -> Set[str]:
    url: str = f"https://pokeapi.co/api/v2/type/{type_name}"
    response = requests.get(url)
    if response.status_code == 200:
        data: Dict[str, Any] = response.json()
        double_damage_from: List[Dict[str, str]] = data["damage_relations"]["double_damage_from"]
        weaknesses: Set[str] = {t["name"] for t in double_damage_from}
        return weaknesses
    return set()

def get_pokemon_height(url: str) -> int:
    response = requests.get(url)
    if response.status_code == 200:
        data: Dict[str, Any] = response.json()
        height: int = data.get("height", 0)
        return height
    return 0

def check_param(types: List[str], weaknesses: Set[str], height: int, key: str, value: str) -> bool:
    if key == "type":
        if value:
            result: bool = value.lower() in [t.lower() for t in types]
            return result
        else:
            return True
    elif key == "weakness":
        if value:
            result: bool = value.lower() in weaknesses
            return result
        else:
            return True
    elif key == "height":
        if value:
            try:
                height = int(height)
                if value == "small":
                    result: bool = height <= 5
                elif value == "medium":
                    result: bool = 5 < height <= 10
                elif value == "large":
                    result: bool = height > 10
                return result
            except ValueError:
                return False
        else:
            return True

def filter_pokemons(pokemons: List[Dict[str, Any]], params: Dict[str, str]) -> List[Dict[str, Any]]:
    filtered_pokemons: List[Dict[str, Any]] = []

    def filter_pokemon(pokemon: Dict[str, Any]) -> bool:
        types: List[str] = get_pokemon_types(pokemon["url"])
        weaknesses: Set[str] = set().union(*(get_type_weaknesses(t) for t in types))
        height: int = get_pokemon_height(pokemon["url"])

        type_passed: bool = True
        weakness_passed: bool = True
        height_passed: bool = True

        if "type" in params:
            type_passed = check_param(types, weaknesses, height, "type", params["type"])

        if "weakness" in params:
            weakness_passed = check_param(types, weaknesses, height, "weakness", params["weakness"])

        if "height" in params:
            height_passed = check_param(types, weaknesses, height, "height", params["height"])

        passed: bool = type_passed and weakness_passed and height_passed

        return passed

    for pokemon in pokemons:
        if filter_pokemon(pokemon):
            filtered_pokemons.append(pokemon)

    return filtered_pokemons

@app.route("/pokemon/<name>")
def pokemon_details(name: str) -> str:
    pokemon_info: Dict[str, Any] = get_pokemon_info(name)
    if pokemon_info:
        return render_template("poke_name.html", pokemon_info=pokemon_info)
    else:
        return redirect("/", code=302)

def get_pokemon_info(name: str) -> Dict[str, Any]:
    pokemon_info: Dict[str, Any] = {}

    api_url: str = f"https://pokeapi.co/api/v2/pokemon/{name.lower()}"
    response = requests.get(api_url)
    if response.status_code == 200:
        data: Dict[str, Any] = response.json()

        pokemon_info["name"] = data["name"].capitalize()
        pokemon_info["image"] = data["sprites"]["front_default"]
        pokemon_info["id"] = data["id"]
        pokemon_info["height"] = data["height"]
        pokemon_info["weight"] = data["weight"]
        abilities: str = ", ".join(ability["ability"]["name"] for ability in data["abilities"])
        pokemon_info["abilities"] = abilities
        base_stats: str = ", ".join(f"{stat['stat']['name'].capitalize()}: {stat['base_stat']}" for stat in data["stats"])
        pokemon_info["base_stats"] = base_stats

        types: List[str] = get_pokemon_types(api_url)
        types_str: str = ", ".join(types)
        pokemon_info["types"] = types_str

        weaknesses: Set[str] = set().union(*(get_type_weaknesses(t) for t in types))
        weaknesses_str: str = ", ".join(weaknesses)
        pokemon_info["weaknesses"] = weaknesses_str

        evolution_chain_url: str = data["species"]["url"]
        evolution_chain_response = requests.get(evolution_chain_url)
        if evolution_chain_response.status_code == 200:
            evolution_chain_data: Dict[str, Any] = evolution_chain_response.json()
            evolution_chain: List[Dict[str, str]] = []
            current_evolution: Dict[str, Any] = evolution_chain_data["evolves_from_species"]
            while current_evolution:
                current_evolution_url: str = current_evolution["url"]
                current_evolution_response = requests.get(current_evolution_url)
                if current_evolution_response.status_code == 200:
                    current_evolution_data: Dict[str, Any] = current_evolution_response.json()
                    evolution_chain.append({
                        "name": current_evolution_data["name"].capitalize(),
                        "image": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{current_evolution_data['id']}.png"
                    })
                    current_evolution = current_evolution_data["evolves_from_species"]
                else:
                    break
            pokemon_info["evolution_chain"] = evolution_chain[::-1]

    return pokemon_info

if __name__ == "__main__":
    app.run(debug=True)
