import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# -------------------------------
# Função para coletar os vídeos
# -------------------------------
def coletar_videos(api_key, channel_id, tipo="all", max_results=100):
    url_base = "https://www.googleapis.com/youtube/v3/"
    
    # 1) Obter o Uploads Playlist ID do canal
    channel_url = f"{url_base}channels?part=contentDetails&id={channel_id}&key={api_key}"
    r = requests.get(channel_url).json()
    
    if "items" not in r or len(r["items"]) == 0:
        return pd.DataFrame(), "Canal não encontrado ou inválido."
    
    uploads_playlist = r["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    
    # 2) Coletar vídeos do canal via playlist
    videos = []
    next_page = None
    total_coletado = 0
    
    while True:
        playlist_url = f"{url_base}playlistItems?part=contentDetails&playlistId={uploads_playlist}&maxResults=50&key={api_key}"
        if next_page:
            playlist_url += f"&pageToken={next_page}"
        
        playlist_data = requests.get(playlist_url).json()
        
        for item in playlist_data.get("items", []):
            videos.append(item["contentDetails"]["videoId"])
            total_coletado += 1
            if total_coletado >= max_results:
                break
        
        if "nextPageToken" in playlist_data and total_coletado < max_results:
            next_page = playlist_data["nextPageToken"]
        else:
            break
    
    # 3) Buscar estatísticas dos vídeos
    video_chunks = [videos[i:i+50] for i in range(0, len(videos), 50)]
    dados = []
    
    for chunk in video_chunks:
        stats_url = f"{url_base}videos?part=snippet,statistics,contentDetails&id={','.join(chunk)}&key={api_key}"
        stats_data = requests.get(stats_url).json()
        
        for v in stats_data.get("items", []):
            duracao = v["contentDetails"]["duration"]
            title = v["snippet"]["title"]
            video_id = v["id"]
            link = f"https://www.youtube.com/watch?v={video_id}"
            
            # Definir tipo (short vs longo)
            segundos = iso8601_para_segundos(duracao)
            is_short = segundos <= 60
            
            if tipo == "shorts" and not is_short:
                continue
            if tipo == "videos" and is_short:
                continue
            
            views = int(v["statistics"].get("viewCount", 0))
            likes = int(v["statistics"].get("likeCount", 0)) if "likeCount" in v["statistics"] else 0
            comments = int(v["statistics"].get("commentCount", 0)) if "commentCount" in v["statistics"] else 0
            
            dados.append({
                "Título": title,
                "Link": link,
                "Views": views,
                "Likes": likes,
                "Comentários": comments,
                "Duração (s)": segundos,
                "Publicado em": v["snippet"]["publishedAt"]
            })
    
    df = pd.DataFrame(dados)
    
    if df.empty:
        return df, "Nenhum vídeo encontrado com os filtros selecionados."
    
    # 4) Ordenar por viralidade (views + likes*3 + comments*5)
    df["Score Viralidade"] = df["Views"] + df["Likes"] * 3 + df["Comentários"] * 5
    df = df.sort_values(by="Score Viralidade", ascending=False).reset_index(drop=True)
    
    return df, None


# -------------------------------
# Função auxiliar para converter ISO8601 → segundos
# -------------------------------
import isodate
def iso8601_para_segundos(duration):
    try:
        return int(isodate.parse_duration(duration).total_seconds())
    except:
        return 0


# -------------------------------
# Interface Streamlit
# -------------------------------
st.title("📊 YouTube Viral Analyzer")
st.write("Analise os vídeos mais virais de um canal do YouTube (incluindo Shorts e Longos).")

api_key = st.text_input("🔑 Sua API Key do YouTube Data API v3")
channel_id = st.text_input("📺 ID do Canal (ex: UC-lHJZR3Gqxm24_Vd_AJ5Yw)")

tipo = st.radio("🎯 Tipo de pesquisa", ["all", "shorts", "videos"], format_func=lambda x: "Todos" if x=="all" else "Só Shorts" if x=="shorts" else "Só Vídeos longos")
limite = st.number_input("📌 Quantidade de vídeos a analisar", min_value=10, max_value=500, value=100, step=10)

if st.button("🚀 Analisar"):
    if not api_key or not channel_id:
        st.error("Preencha a API Key e o ID do canal antes de continuar.")
    else:
        df, erro = coletar_videos(api_key, channel_id, tipo, limite)
        
        if erro:
            st.error(erro)
        else:
            st.success(f"✅ Foram analisados {len(df)} vídeos do canal.")
            
            # Mostrar TOP 5
            st.subheader("🏆 TOP 5 mais virais")
            st.dataframe(df.head(5)[["Título", "Link", "Views", "Likes", "Comentários", "Score Viralidade"]])
            
            # Mostrar tabela completa
            st.subheader("📋 Resultados completos")
            st.dataframe(df)
            
            # Exportar CSV
            csv = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("📥 Baixar CSV completo", csv, "resultados_youtube.csv", "text/csv", key="download_csv")
