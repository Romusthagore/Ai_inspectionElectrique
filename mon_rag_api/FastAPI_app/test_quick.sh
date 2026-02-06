#!/bin/bash

API_URL="http://localhost:8001"
echo "🚀 Test rapide de l'API RAG"
echo "=========================="

echo -e "\n1. ✅ Health Check:"
curl -s "$API_URL/health" | python -m json.tool

echo -e "\n2. ✅ Status Services:"
curl -s "$API_URL/api/v1/status" | python -m json.tool | head -20

echo -e "\n3. ✅ Recherche: 'protection différentielle'"
curl -s -X POST "$API_URL/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "protection différentielle", "top_k": 2}' \
  | python -m json.tool

echo -e "\n4. ✅ Autocomplétion: 'Remplacer'"
curl -s -X POST "$API_URL/api/v1/autocomplete" \
  -H "Content-Type: application/json" \
  -d '{"query": "Remplacer"}' \
  | python -m json.tool

echo -e "\n5. ✅ Reformulation: 'cable abimé'"
curl -s -X POST "$API_URL/api/v1/reformulate" \
  -H "Content-Type: application/json" \
  -d '{"text": "cable abimé"}' \
  | python -m json.tool

echo -e "\n6. ✅ Extraction norme:"
curl -s -X POST "$API_URL/api/v1/extract_norme" \
  -H "Content-Type: application/json" \
  -d '{"observation": "protection manquante", "prescriptions": ["Installer protection"]}' \
  | python -m json.tool

echo -e "\n🎉 Tests terminés! Accédez à la documentation: $API_URL/docs"
