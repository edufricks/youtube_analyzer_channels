import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ========================
# Função para capturar o channelId correto
# ========================
def get_channel_id(api_key, channel_input):
    base_url = "https://www.googleapis.com/youtube/v3/"
    
    # Caso seja URL completa
    if "youtube.com" in channel_input:
        if "channel/" in channel_input:
            # URL tipo: https://www.youtube.com/channel/UCxxxx
            return channel_input.split("channel/")[-1].split("/")[0]
        elif "@" in channel_input:
            # URL tipo: https://www.youtube.com/@nome
            username = channel_input.split("@")[-1].split("/")[0]
            url = f"{base_url}channels?part=id&forUsername={username}&key={api_key}"
            resp = requests.get(url).json()
            if "items" in resp and resp["items"]:
                return resp["items"][0]["id"]
            # fallback: tentar via search
            search_url = f"{base_url}search?part=snippet&type=channel&q={username}&key={api_key}"
            resp = requests.get(search_url).json()
            if "items" in resp and resp["items"]:
                return resp["items"][0]["snippet"]["channelId"]
    
    # Caso seja apenas @username
    if channel_input.startswith("@"):
        username = channel_input[1:]
        url = f"{base_url}channels?part=id&forUsername={username}&key={api_key}"
        resp = requests.get(url).json()
        if "items" in resp and resp["items"]:
            return resp["items"][0]["id"]
        # fallback via search
        search_url = f"{base_url}search?part=snippet&type=channel&q={username}&key={api_key}"
        resp = requests.get(search_url).json()
        if "items" in resp and resp["items"]:
            return resp["items"][0]["snippet"]["channelId"]

    # Caso o usuário já insira diretamente o channelId
    return channel_input

# ========================
# Função para coletar vídeos do canal
# ========================
def get_videos(api_key, channel_id, max_results=50, search_type="all", fetch_all=False):
    base_url = "https://www.googleapis.com/youtube/v3/search"
    videos = []
    next_page_token = None

    while True:
        url = f"{base_url}?key={api_key}&channelId={channel_id}&part=snippet,id&order=date&maxResults=50"
        if next_page_token:
            url += f"&pageToken={next_page_token}"

        resp = requests.get(url).json()
        for item in resp.get("items", []):
            if item["id"]["kind"] == "youtube#video":
                if search_type == "shorts" and "shorts" not in item["snippet"]["title"].lower():
                    continue
                if search_type == "longs" and "shorts" in item["snippet"]["title"].lower():
                    continue
                videos.append(item["id"]["videoId"])

        next_page_token = resp.get("nextPageToken")
        if not next_page_token or (not fetch_all and len(videos) >= max_results):
            break

    return videos[:max_results] if not fetch_all else videos

# ========================
# Função para pegar estatísticas dos vídeos
# ========================
def get_video_stats(api_key, video_ids):
    stats = []
    base_url = "https://www.googleapis.com/youtube/v3/videos"

    for i in range(0, len(video_ids), 50):
        ids = ",".join(video_ids[i:i+50])
        url = f"{base_url}?part=statistics,snippet&id={ids}&key={api_key}"
        resp = requests.get(url).json()
        for item in resp.get("items", []):
            stats.append({
                "Título": item["snippet"]["title"],
                "Publicado em": item["snippet"]["publishedAt"],
                "Views": int(item["statistics"].get("viewCount", 0)),
                "Likes": int(item["statistics"].get("likeCount", 0)),
                "Comentários": int(item["statistics"].get("commentCount", 0)),
                "Link": f"https://youtu.be/{item['id']}"
            })
    return stats

# ========================
# Fórmula de viralidade
# ========================
def calcular_viralidade(df):
    df["Viralidade"] = (df["Views"] * 0.6) + (df["Likes"] * 3) + (df["Comentários"] * 5)
    return df

# ========================
# Streamlit App
# ========================
st.set_page_config(page_title="YouTube Viral Analyzer", layout="wide")

st.title("📊 YouTube Viral Analyzer")

api_key = st.text_input("🔑 Insira sua API Key do YouTube", type="password")
canal = st.text_input("📺 Insira o canal (ex: @canal, URL ou Channel ID):")

tipo_pesquisa = st.radio("Tipo de pesquisa:", ["Todos os vídeos", "Apenas Shorts", "Apenas Longos"])
qtd_videos_opcao = st.radio("Quantos vídeos deseja analisar?", ["Canal inteiro", "Definir quantidade"])
qtd_videos = st.number_input("Digite o número de vídeos (ex: 200)", min_value=1, max_value=1000, value=100) if qtd_videos_opcao == "Definir quantidade" else None

if st.button("🔍 Analisar Canal") and api_key and canal:
    st.info("⏳ Coletando vídeos, aguarde...")

    try:
        channel_id = get_channel_id(api_key, canal)
        search_type = "all" if tipo_pesquisa == "Todos os vídeos" else ("shorts" if tipo_pesquisa == "Apenas Shorts" else "longs")
        fetch_all = qtd_videos_opcao == "Canal inteiro"
        video_ids = get_videos(api_key, channel_id, max_results=qtd_videos or 50, search_type=search_type, fetch_all=fetch_all)

        if not video_ids:
            st.error("Nenhum vídeo encontrado nesse canal com os filtros escolhidos.")
        else:
            dados = get_video_stats(api_key, video_ids)
            df = pd.DataFrame(dados)
            df = calcular_viralidade(df)
            df = df.sort_values(by="Viralidade", ascending=False).reset_index(drop=True)

            st.success(f"{len(df)} vídeos analisados com sucesso!")

            st.subheader("🏆 Top 5 vídeos mais virais (ranking pela fórmula):")
            st.dataframe(df.head(5))

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Baixar CSV completo", csv, "analise_youtube.csv", "text/csv")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
