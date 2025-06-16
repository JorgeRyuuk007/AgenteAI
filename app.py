import os
import json
import requests
import logging
from flask import Flask, request, jsonify
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
import tempfile
import base64

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializa Flask
app = Flask(__name__)

# Configurações
Z_API_TOKEN = os.getenv('Z_API_TOKEN')
Z_API_INSTANCE = os.getenv('Z_API_INSTANCE')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
Z_API_BASE_URL = "https://api.z-api.io"

# Verifica se as variáveis estão configuradas
if not all([Z_API_TOKEN, Z_API_INSTANCE, GROQ_API_KEY]):
    logger.error("ERRO: Variáveis de ambiente não configuradas!")
    logger.error(f"Z_API_TOKEN: {'✓' if Z_API_TOKEN else '✗'}")
    logger.error(f"Z_API_INSTANCE: {'✓' if Z_API_INSTANCE else '✗'}")
    logger.error(f"GROQ_API_KEY: {'✓' if GROQ_API_KEY else '✗'}")

# Inicializa cliente Groq (SEM parâmetros extras)
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    logger.info("Cliente Groq inicializado com sucesso")
except Exception as e:
    logger.error(f"Erro ao inicializar Groq: {str(e)}")
    groq_client = None

# Dicionário para manter contexto básico das conversas
conversation_context = {}

# Prompt da Lina
LINA_PROMPT = """NOME: Lina

INTRODUÇÃO INICIAL:
Se for a primeira mensagem do usuário, responda exatamente:
"Hey! Lina na área 🚀 Considere seus problemas resolvidos (ou pelo menos, vamos tentar juntos!). O que tá rolando hoje?"

IDENTIDADE:
- Assistente versátil e inteligente
- Especialista generalista com conhecimento profundo em múltiplas áreas
- Personalidade acolhedora, prática e confiável

ÁREAS DE EXPERTISE:
• Vida Prática: Culinária, organização, finanças pessoais, DIY
• Tecnologia: Programação, IA, segurança digital, tendências tech
• Bem-estar: Saúde física e mental, exercícios, nutrição, mindfulness
• Educação: Técnicas de estudo, explicações didáticas, orientação acadêmica
• Carreira: Desenvolvimento profissional, empreendedorismo, produtividade
• Relacionamentos: Comunicação, resolução de conflitos, inteligência emocional
• Cultura & Lazer: Arte, música, literatura, viagens, hobbies
• Ciências: Explicações científicas acessíveis, curiosidades, inovações
• Atualidades: Análise contextualizada de eventos e tendências

DIRETRIZES DE RESPOSTA:
1. ESCUTE primeiro - identifique a real necessidade por trás da pergunta
2. PERSONALIZE - ajuste tom e profundidade conforme o contexto
3. SEJA PRÁTICA - forneça passos acionáveis e exemplos concretos
4. ESTRUTURE - use formatação clara quando apropriado
5. VALIDE - reconheça sentimentos e preocupações quando relevante

PRINCÍPIOS:
- Honestidade: "Não tenho certeza sobre isso, mas posso pesquisar" ou "Isso está fora da minha área, mas posso sugerir..."
- Empatia: Reconheça o contexto emocional das perguntas
- Clareza: Evite jargões desnecessários, explique termos técnicos
- Proatividade: Antecipe perguntas relacionadas e ofereça recursos extras
- Segurança: Sempre priorize o bem-estar do usuário em suas orientações

ESTILO DE COMUNICAÇÃO:
- Amigável sem ser invasiva
- Profissional sem ser distante
- Entusiasmada sem exageros
- Use emojis com moderação para dar leveza (1-2 por resposta no máximo)
- Varie entre respostas curtas e detalhadas conforme a necessidade

CASOS ESPECIAIS:
- Urgências: Seja direta e rápida, foque no essencial
- Aprendizado: Use analogias e divida conceitos complexos
- Criatividade: Inspire com múltiplas perspectivas e ideias
- Problemas pessoais: Ouça com empatia, sugira sem impor"""

def send_message_to_whatsapp(phone, message):
    """Envia mensagem de texto via Z-API"""
    try:
        url = f"{Z_API_BASE_URL}/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/send-text"
        
        payload = {
            "phone": phone,
            "message": message
        }
        
        headers = {
            "Content-Type": "application/json",
            "Client-Token": Z_API_TOKEN
        }
        
        logger.info(f"Enviando mensagem para {phone}...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Resposta Z-API: {result}")
        logger.info(f"Mensagem enviada com sucesso para {phone}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem para {phone}: {str(e)}")
        return False

def download_audio_from_z_api(message_id):
    """Baixa arquivo de áudio do Z-API"""
    try:
        # Tenta diferentes endpoints do Z-API para download
        urls = [
            f"{Z_API_BASE_URL}/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/download-media/{message_id}",
            f"{Z_API_BASE_URL}/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/download-media"
        ]
        
        headers = {
            "Client-Token": Z_API_TOKEN
        }
        
        for url in urls:
            try:
                if "download-media/" in url:
                    response = requests.get(url, headers=headers, timeout=30)
                else:
                    params = {"messageId": message_id}
                    response = requests.get(url, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Resposta download: {data}")
                    
                    # Diferentes formatos de resposta do Z-API
                    if 'base64' in data:
                        return base64.b64decode(data['base64'])
                    elif 'media' in data and 'base64' in data['media']:
                        return base64.b64decode(data['media']['base64'])
                    elif 'file' in data:
                        # Se retornar URL, baixa o arquivo
                        file_response = requests.get(data['file'], timeout=30)
                        return file_response.content
                        
            except Exception as e:
                logger.warning(f"Tentativa de download falhou com {url}: {str(e)}")
                continue
        
        logger.error("Todas as tentativas de download falharam")
        return None
        
    except Exception as e:
        logger.error(f"Erro ao baixar áudio: {str(e)}")
        return None

def transcribe_audio(audio_data):
    """Transcreve áudio usando Whisper da Groq"""
    try:
        if not groq_client:
            logger.error("Cliente Groq não inicializado")
            return None
            
        # Salva temporariamente o arquivo de áudio
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
        
        logger.info(f"Transcrevendo áudio temporário: {temp_audio_path}")
        
        # Transcreve com Whisper
        with open(temp_audio_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language="pt"
            )
        
        # Remove arquivo temporário
        os.unlink(temp_audio_path)
        
        transcription_text = transcription.text.strip()
        logger.info(f"Transcrição realizada: {transcription_text}")
        return transcription_text
        
    except Exception as e:
        logger.error(f"Erro na transcrição: {str(e)}")
        # Remove arquivo temporário em caso de erro
        try:
            if 'temp_audio_path' in locals():
                os.unlink(temp_audio_path)
        except:
            pass
        return None

def get_lina_response(user_message, phone_number):
    """Gera resposta da Lina usando Groq"""
    try:
        if not groq_client:
            return "Desculpe, estou com problemas técnicos no momento. Tente novamente em alguns minutos! 😅"
            
        # Verifica se é primeira mensagem do usuário
        is_first_message = phone_number not in conversation_context
        
        # Inicializa ou recupera contexto
        if is_first_message:
            conversation_context[phone_number] = {
                "messages": [],
                "created_at": datetime.now().isoformat()
            }
        
        context = conversation_context[phone_number]
        
        # Prepara mensagens para o modelo
        messages = [
            {"role": "system", "content": LINA_PROMPT}
        ]
        
        # Adiciona histórico recente (últimas 10 interações)
        for msg in context["messages"][-10:]:
            messages.append(msg)
        
        # Adiciona mensagem atual
        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"Gerando resposta com Groq para: {user_message[:50]}...")
        
        # Gera resposta com Groq
        response = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        lina_response = response.choices[0].message.content
        
        # Atualiza contexto
        context["messages"].append({"role": "user", "content": user_message})
        context["messages"].append({"role": "assistant", "content": lina_response})
        
        # Limita tamanho do histórico
        if len(context["messages"]) > 20:
            context["messages"] = context["messages"][-20:]
        
        logger.info(f"Resposta gerada: {lina_response[:100]}...")
        return lina_response
        
    except Exception as e:
        logger.error(f"Erro ao gerar resposta: {str(e)}")
        return "Ops! 😅 Tive um pequeno problema técnico. Pode repetir sua mensagem?"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint principal do webhook Z-API"""
    try:
        # Log do payload recebido
        data = request.get_json()
        logger.info(f"Webhook recebido: {json.dumps(data, indent=2)}")
        
        # Verifica se é mensagem recebida
        if not data:
            logger.warning("Payload vazio recebido")
            return jsonify({"status": "ignored"}), 200
            
        # Diferentes tipos de callback do Z-API
        message_type_field = data.get('type') or data.get('event')
        if message_type_field not in ['ReceivedCallback', 'received'] and message_type_field is not None:
            logger.info(f"Tipo de callback ignorado: {message_type_field}")
            return jsonify({"status": "ignored"}), 200
        
        # Extrai informações da mensagem
        phone = data.get('phone') or data.get('from')
        message_type = data.get('messageType') or data.get('type')
        
        if not phone:
            logger.warning("Mensagem sem número de telefone")
            return jsonify({"status": "error", "message": "No phone number"}), 400
        
        # Remove caracteres especiais do número
        phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        logger.info(f"Processando mensagem de {phone} - Tipo: {message_type}")
        
        user_message = None
        
        # Processa mensagem de texto
        if message_type == 'text':
            text_data = data.get('text', {})
            user_message = text_data.get('message', '')
            logger.info(f"Mensagem de texto de {phone}: {user_message}")
        
        # Processa mensagem de áudio
        elif message_type in ['audio', 'ptt']:
            logger.info(f"Áudio recebido de {phone}")
            
            # Obtém ID do áudio
            audio_info = data.get('audio', {}) or data.get('ptt', {})
            message_id = audio_info.get('messageId') or data.get('messageId')
            
            if message_id:
                logger.info(f"Processando áudio com ID: {message_id}")
                
                # Baixa e transcreve áudio
                audio_data = download_audio_from_z_api(message_id)
                if audio_data:
                    transcription = transcribe_audio(audio_data)
                    if transcription and transcription.strip():
                        user_message = transcription
                        logger.info(f"Transcrição realizada: {transcription}")
                        
                        # Envia confirmação da transcrição
                        send_message_to_whatsapp(
                            phone, 
                            f"🎤 *Entendi seu áudio:* _{transcription}_"
                        )
                    else:
                        send_message_to_whatsapp(
                            phone,
                            "Desculpe, não consegui entender o áudio. Pode tentar enviar uma mensagem de texto? 🎤"
                        )
                        return jsonify({"status": "transcription_failed"}), 200
                else:
                    send_message_to_whatsapp(
                        phone,
                        "Não consegui processar o áudio. Pode tentar novamente? 🎤"
                    )
                    return jsonify({"status": "download_failed"}), 200
            else:
                logger.error("ID do áudio não encontrado")
                return jsonify({"status": "error", "message": "Audio ID not found"}), 400
        
        # Se não há mensagem para processar, ignora
        if not user_message or not user_message.strip():
            logger.info("Mensagem vazia ou inválida, ignorando")
            return jsonify({"status": "ignored"}), 200
        
        # Gera resposta da Lina
        logger.info(f"Gerando resposta da Lina para: {user_message}")
        lina_response = get_lina_response(user_message, phone)
        
        # Envia resposta
        if send_message_to_whatsapp(phone, lina_response):
            logger.info(f"Conversa processada com sucesso para {phone}")
            return jsonify({"status": "success"}), 200
        else:
            logger.error(f"Falha ao enviar resposta para {phone}")
            return jsonify({"status": "send_failed"}), 500
        
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    return jsonify({
        "status": "healthy",
        "service": "Lina WhatsApp Agent",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "z_api_configured": bool(Z_API_TOKEN and Z_API_INSTANCE),
            "groq_configured": bool(GROQ_API_KEY),
            "groq_client_ready": groq_client is not None
        },
        "conversation_active": len(conversation_context)
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Página inicial"""
    return jsonify({
        "agent": "Lina - Assistente IA para WhatsApp",
        "version": "1.0",
        "status": "online" if groq_client else "partially_online",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health"
        },
        "features": [
            "Conversas por texto",
            "Transcrição de áudios",
            "Múltiplas áreas de conhecimento",
            "Contexto de conversa"
        ]
    }), 200

# Endpoint de teste (remover em produção)
@app.route('/test', methods=['POST'])
def test_endpoint():
    """Endpoint para testar funcionalidades"""
    try:
        data = request.get_json()
        test_type = data.get('type', 'message')
        
        if test_type == 'message':
            message = data.get('message', 'Olá!')
            phone = data.get('phone', '5511999999999')
            
            response = get_lina_response(message, phone)
            return jsonify({
                "status": "success",
                "input": message,
                "output": response
            })
            
        elif test_type == 'health':
            return health_check()
            
        return jsonify({"status": "unknown_test_type"}), 400
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Verifica configurações essenciais
    if not all([Z_API_TOKEN, Z_API_INSTANCE, GROQ_API_KEY]):
        logger.error("ERRO CRÍTICO: Variáveis de ambiente não configuradas!")
        logger.error("Verifique Z_API_TOKEN, Z_API_INSTANCE e GROQ_API_KEY")
        # Não interrompe em produção, só alerta
        
    logger.info("🤖 Lina WhatsApp Agent iniciando...")
    logger.info(f"📱 Z-API Instance: {Z_API_INSTANCE}")
    logger.info(f"🧠 Groq Client: {'✓ Configurado' if groq_client else '✗ Erro'}")
    
    # Inicia servidor
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 Servidor iniciando na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
