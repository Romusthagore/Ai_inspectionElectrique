"""
Version simplifiée et corrigée pour charger Mistral-7B
"""
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from pathlib import Path

# Configuration
LOCAL_DIR = "/home/user/models/mistral-7b"
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"

def find_model_path():
    """
    Trouve le bon chemin vers le modèle dans le cache HuggingFace
    """
    print(" Recherche du modèle dans le cache...")
    
    cache_path = Path(LOCAL_DIR)
    
    # Méthode 1: Chercher dans models--mistralai--Mistral-7B-Instruct-v0.2
    model_cache = cache_path / "models--mistralai--Mistral-7B-Instruct-v0.2"
    if model_cache.exists():
        print(f"✓ Trouvé: {model_cache}")
        
        # Chercher le snapshot le plus récent
        snapshots_dir = model_cache / "snapshots"
        if snapshots_dir.exists():
            versions = [d for d in snapshots_dir.iterdir() if d.is_dir()]
            if versions:
                latest = max(versions, key=lambda p: p.stat().st_mtime)
                print(f"✓ Snapshot: {latest.name}")
                return str(latest)
    
    # Méthode 2: Chercher n'importe quel snapshot
    snapshots = list(cache_path.rglob("snapshots/*/config.json"))
    if snapshots:
        snapshot_dir = snapshots[0].parent
        print(f"✓ Snapshot trouvé: {snapshot_dir}")
        return str(snapshot_dir)
    
    # Méthode 3: Si rien trouvé, retourner le nom du modèle (téléchargement)
    print(f"  Aucun cache trouvé, utilisera: {MODEL_NAME}")
    return MODEL_NAME

def load_mistral():
    """
    Charge Mistral-7B de manière robuste
    """
    print("\n" + "="*60)
    print(" CHARGEMENT DE MISTRAL-7B")
    print("="*60)
    
    # Trouver le bon chemin
    model_path = find_model_path()
    print(f"\n Chemin utilisé: {model_path}")
    
    try:
        # Charger le tokenizer
        print("\n Chargement du tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            legacy=False,
            trust_remote_code=True
        )
        print("    Tokenizer OK")
        
        # Charger le modèle
        print("\n Chargement du modèle (peut prendre 1-2 min)...")
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        print("    Modèle OK")
        
        # Device
        device = next(model.parameters()).device
        print(f"\n Device: {device}")
        
        return tokenizer, model, device
        
    except Exception as e:
        print(f"\n Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def test_inference(tokenizer, model, device):
    """
    Test d'inférence simple
    """
    print("\n" + "="*60)
    print(" TEST D'INFÉRENCE")
    print("="*60)
    
    prompt = "<s>[INST] Quelle est la capitale de la France ? Réponds en un mot. [/INST]"
    
    print(f"\n Prompt: {prompt}")
    print("\n Génération en cours...")
    
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(
        outputs[0][inputs['input_ids'].shape[1]:], 
        skip_special_tokens=True
    )
    
    print(f"\n Réponse: {response.strip()}")
    print("\n TEST RÉUSSI!")

def create_client_class(tokenizer, model, device):
    """
    Crée une classe client réutilisable
    """
    
    class MistralClient:
        def __init__(self, tokenizer, model, device):
            self.tokenizer = tokenizer
            self.model = model
            self.device = device
        
        def invoke(self, prompt, max_tokens=200, temperature=0.7):
            """Génère une réponse"""
            # Formater au format Mistral
            if not prompt.startswith("<s>[INST]"):
                formatted_prompt = f"<s>[INST] {prompt} [/INST]"
            else:
                formatted_prompt = prompt
            
            inputs = self.tokenizer(
                formatted_prompt, 
                return_tensors="pt",
                truncation=True,
                max_length=4096
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.9,
                    do_sample=temperature > 0,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:], 
                skip_special_tokens=True
            )
            
            return response.strip()
        
        def __call__(self, prompt, **kwargs):
            """Permet d'appeler directement l'instance"""
            return self.invoke(prompt, **kwargs)
    
    return MistralClient(tokenizer, model, device)

def main():
    """
    Script principal
    """
    print("\n" + "="*70)
    print(" MISTRAL-7B - CHARGEMENT SIMPLIFIÉ")
    print("="*70)
    
    # Charger le modèle
    tokenizer, model, device = load_mistral()
    
    if tokenizer is None or model is None:
        print("\n❌ Échec du chargement")
        return None
    
    # Test d'inférence
    test_inference(tokenizer, model, device)
    
    # Créer le client
    print("\n" + "="*60)
    print(" CRÉATION DU CLIENT")
    print("="*60)
    
    client = create_client_class(tokenizer, model, device)
    
    print("\n Client créé! Exemples d'utilisation:")
    print("""
# Utilisation simple
response = client("Qu'est-ce que Python ?")
print(response)

# Avec paramètres
response = client(
    "Explique la photosynthèse en 3 phrases",
    max_tokens=150,
    temperature=0.5
)
print(response)
    """)
    
    # Test interactif
    print("\n" + "="*60)
    print(" TEST INTERACTIF")
    print("="*60)
    
    questions = [
        "Quelle est la capitale de l'Allemagne ?",
        "Cite 3 langages de programmation populaires",
        "Qu'est-ce qu'un transformeur en IA ?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n❓ Question {i}: {question}")
        response = client(question, max_tokens=100)
        print(f" Réponse: {response}")
        print("-" * 60)
    
    print("\n" + "="*60)
    print("✨ TOUT EST PRÊT!")
    print("="*60)
    
    return client

if __name__ == "__main__":
    client = main()
    
    # Sauvegarder le client globalement pour réutilisation
    if client:
        print("\n Client sauvegardé dans la variable 'client'")
        print("   Utilisez: client('votre question')")