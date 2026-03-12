#!/bin/bash

# Co-STORM with Hybrid Retrieval Runner
# Uses OpenRouter API for both LLM and Embedding

echo "================================================================================"
echo "🚀 Co-STORM Thai with Hybrid Retrieval"
echo "================================================================================"
echo ""
echo "💡 This script will:"
echo "   1. Check for OPENROUTER_API_KEY"
echo "   2. Run Co-STORM with best quality retrieval (Vector + BM25 + Reranking)"
echo ""

# Check if OPENROUTER_API_KEY is already set
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠️  OPENROUTER_API_KEY not found in environment"
    echo ""
    echo "Please enter your OpenRouter API key:"
    echo "(Get it from: https://openrouter.ai/keys)"
    echo ""
    read -p "API Key: " OPENROUTER_API_KEY
    
    if [ -z "$OPENROUTER_API_KEY" ]; then
        echo ""
        echo "❌ Error: No API key provided"
        exit 1
    fi
    
    export OPENROUTER_API_KEY
    echo ""
    echo "✅ API key set for this session"
else
    echo "✅ Using OPENROUTER_API_KEY from environment"
fi

echo ""
echo "================================================================================"
echo "🔧 Starting Co-STORM..."
echo "================================================================================"
echo ""

# Run the script with venv Python
../.venv/bin/python test_costorm_hybrid.py

echo ""
echo "================================================================================"
echo "✅ Session complete"
echo "================================================================================"
