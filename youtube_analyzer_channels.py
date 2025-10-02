import streamlit as st
import pandas as pd
import requests

# ===============================
# Função para normalizar o canal
# ===============================
def obter_channel_id(api_key, entrada):
    url_base = "https://www.googleapis.com/youtube/v3/"

    # Se já for um channelId válido (começa com UC)
    if entrada.startswith("UC"):
        return entrada

    # Se for username estilo @manualjr
    if entrada.startswith("@"):
        username = entrada[1:]
        url = f"{url_base}search?part=snippet&type=channel&q={username}&key={api_key}"
        r = requests.get(url).json()
        if "items" in r and len(r["items"]) > 0:
            return r["items"][0]["snippet"]["channelId"]

    # Se for URL de canal
    if "youtube.com" in entrada:
        if "/channel/" in entrada:  # URL com channelId
            return entrada.split("/channel/")[-1].split("/")[0]
        if "/@" in entrada:  # URL com @username
            username = entrada.split("/@")[-1].split("/")[0]
            url = f"{url_base}search?part=snippet&type=channel&q={username}&key={api_key}"
            r = requests.get(url).json()
            if "items" in r and len(r["items"]) > 0:
                return r["items"][0]["snippet"]["channelId"]

    return None

# ===============================
# Função para coletar vídeos
# ===============================
def coletar_videos(api_key, channel_input, tipo="all"):
    channel_id = obter_channel_id(api_key, channel_input)
    if not channel_id:
        return pd.DataFrame(), "Canal não encontrado ou inválido."

    url_base = "https://www.googleapis.com/youtube/v3/"
    videos = []
    page_token = None

    while True:
        url = f"{url_base}search?part=snippet&channelId={channel_id}&maxResults=50&order=date&type=video&key={api_key}"
        if page_token:
            url += f"&pageToken={page_token}"

        r = requests.get(url).json()
        if "items" not in r:
            break

        for item in r["items"]:
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            published = item["snippet"]["publishedAt"]

            # detalhes do vídeo
            url_stats = f"{url_base}videos?part=statistics,contentDetails&id={video_id}&key={api_key}"
            stats = requests.get(url_stats).json()

            if "items" not in stats or not stats["items"]:
                continue

            stats_item = stats["items"][0]
            duration = stats_item["contentDetails"]["duration"]
            views = int(stats_item["statistics"].get("viewCount", 0))

            # Filtrar shorts (menos de 60s) ou longos
            is_short = "PT" in duration and "M" not in duration and "H" not in duration
            if tipo == "shorts" and not is_short:
                continue
            if tipo == "longos" and is_short:
                continue

            videos.append({
                "Título": title,
                "Publicado em": published,
                "Views": views,
                "Link": f"https://youtu.be/{video_id}"
            })

        page_token = r.get("nextPageToken")
        if not page_token:
            break

    df = pd.DataFrame(videos)
    if not df.empty:
        df = df.sort_values(by="Views", ascending=False).reset_index(drop=True)

    return df, None

# ===============================
# Interface Streamlit
# ===============================
st.title("📊 YouTube Viral Videos Monitor")
st.write("Analise os vídeos mais virais de um canal do YouTube. Informe o canal e sua chave da API.")

api_key = st.text_input("🔑 Insira sua API Key do YouTube Data API v3", type="password")
channel_input = st.text_input("📺 Digite o canal (ID, @username ou URL):")
tipo = st.selectbox("Tipo de pesquisa:", ["all", "shorts", "longos"])

if st.button("Analisar canal"):
    if not api_key or not channel_input:
        st.error("Preencha todos os campos.")
    else:
        with st.spinner("Coletando vídeos... isso pode levar alguns minutos..."):
            df, erro = coletar_videos(api_key, channel_input, tipo)
            if erro:
                st.error(erro)
            elif df.empty:
                st.warning("Nenhum vídeo encontrado.")
            else:
                st.success(f"✅ {len(df)} vídeos analisados!")
                st.dataframe(df.head(10))  # mostra os 10 mais virais
                csv = df.to_csv(index=False)
                st.download_button("📥 Baixar CSV completo", csv, "youtube_videos.csv", "text/csv")
