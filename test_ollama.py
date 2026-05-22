import importlib.util
import sys
import os

# Set environment API_KEY to empty to force Ollama fallback
os.environ["OPENROUTER_API_KEY"] = ""

script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "scripts", "gen-metadata.py"))
spec = importlib.util.spec_from_file_location("gen_metadata", script_path)
gen_metadata = importlib.util.module_from_spec(spec)
sys.modules["gen_metadata"] = gen_metadata
spec.loader.exec_module(gen_metadata)

test_prompt = "A lighthouse on a rocky outcrop, beam pointing into solid black wall of fog"
print(f"Testing prompt: {test_prompt}")
result = gen_metadata.generate_seo_metadata(test_prompt)
print("Result:")
print(result)
