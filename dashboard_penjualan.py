# dashboard_penjualan.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
import plotly.express as px

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="Dashboard Penjualan Marketplace",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# SECRETS (Aman - tidak terlihat di code)
# ============================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# LOAD DATA
# ============================================
@st.cache_data(ttl=300)
def load_data(start_date, end_date, marketplace, statuses, kategoris, gudangs, skus):
    """Load data penjualan dengan filter"""
    try:
        supabase = init_supabase()
        
        query = supabase.table("data_penjualan").select("*")
        query = query.gte("tanggal", start_date).lte("tanggal", end_date)
        
        if marketplace != "semua":
            query = query.eq("sumber_marketplace", marketplace)
        if statuses:
            query = query.in_("status_normal", statuses)
        if kategoris:
            query = query.in_("kategori", kategoris)
        if gudangs:
            query = query.in_("gudang_alias", gudangs)
        if skus:
            query = query.in_("sku_alias", skus)
        
        df = pd.DataFrame(query.execute().data)
        
        if df.empty:
            return df
            
        df['tanggal'] = pd.to_datetime(df['tanggal'])
        df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0)
        df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_iklan(start_date, end_date, marketplace):
    """Load data iklan dengan filter"""
    try:
        supabase = init_supabase()
        query = supabase.table("data_iklan").select("*")
        query = query.gte("tanggal", start_date).lte("tanggal", end_date)
        
        if marketplace != "semua":
            query = query.eq("sumber_marketplace", marketplace)
        
        df = pd.DataFrame(query.execute().data)
        if not df.empty:
            df['biaya_iklan'] = pd.to_numeric(df['biaya_iklan'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error loading iklan: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_filter_options():
    """Get unique values untuk filter dropdown"""
    try:
        supabase = init_supabase()
        
        def get_unique(column, limit=None):
            data = supabase.table("data_penjualan").select(column).execute().data
            values = list(set([d[column] for d in data if d[column]]))
            if limit:
                values = values[:limit]
            return sorted(values)
        
        return {
            'marketplaces': get_unique("sumber_marketplace"),
            'statuses': get_unique("status_normal"),
            'kategoris': get_unique("kategori"),
            'gudangs': get_unique("gudang_alias"),
            'skus': get_unique("sku_alias", limit=500)
        }
    except Exception as e:
        st.error(f"Error getting options: {e}")
        return {'marketplaces': [], 'statuses': [], 'kategoris': [], 'gudangs': [], 'skus': []}

# ============================================
# SIDEBAR - FILTER
# ============================================
st.sidebar.title("🔧 Filter Data")

# Load options
options = get_filter_options()

# Tanggal filter
st.sidebar.subheader("📅 Periode")
col1, col2 = st.sidebar.columns(2)
default_start = datetime.now() - timedelta(days=30)
default_end = datetime.now()

with col1:
    start_date = st.date_input("Dari", default_start)
with col2:
    end_date = st.date_input("Sampai", default_end)

start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

# Marketplace
marketplace = st.sidebar.selectbox(
    "🏪 Marketplace",
    options=["semua"] + options['marketplaces']
)

# Multiselect filters
statuses = st.sidebar.multiselect("📌 Status Pesanan", options['statuses'])
kategoris = st.sidebar.multiselect("📦 Kategori Produk", options['kategoris'])
gudangs = st.sidebar.multiselect("🏭 Gudang", options['gudangs'])
skus = st.sidebar.multiselect("🔖 SKU", options['skus'])

# Apply button
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Terapkan Filter", type="primary", use_container_width=True):
    st.rerun()

# ============================================
# MAIN CONTENT
# ============================================
st.title("📊 Dashboard Penjualan Marketplace")
st.caption(f"📅 Periode: **{start_str}** s/d **{end_str}** | 🏪 Marketplace: **{marketplace}**")

# Load data
with st.spinner("Memuat data..."):
    df = load_data(start_str, end_str, marketplace, statuses, kategoris, gudangs, skus)
    df_iklan = load_iklan(start_str, end_str, marketplace)

# Check empty
if df.empty:
    st.warning("⚠️ Tidak ada data untuk filter yang dipilih. Silakan ubah filter.")
    st.stop()

# ============================================
# METRICS
# ============================================
total_penjualan = df['total'].sum()
total_pesanan = df['no_pesanan'].nunique()
total_qty = df['qty'].sum()
total_iklan = df_iklan['biaya_iklan'].sum() if not df_iklan.empty else 0
roas = total_penjualan / total_iklan if total_iklan > 0 else 0

st.subheader("💰 Ringkasan ROAS")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("Total Penjualan", f"Rp {total_penjualan:,.0f}".replace(",", "."))
with c2:
    st.metric("Biaya Iklan", f"Rp {total_iklan:,.0f}".replace(",", "."))
with c3:
    roas_display = f"{roas:.2f}x" if roas < 999 else "∞"
    st.metric("ROAS", roas_display)
with c4:
    efisiensi = "Sangat Baik" if roas >= 5 else "Baik" if roas >= 2 else "Perlu Optimasi" if roas > 0 else "-"
    st.metric("Efisiensi", efisiensi)
with c5:
    persen_iklan = (total_iklan / total_penjualan * 100) if total_penjualan > 0 else 0
    st.metric("Iklan vs Penjualan", f"{persen_iklan:.1f}%")

# ============================================
# TABS
# ============================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📦 Analisis Kategori", "🔖 Analisis SKU"])

# ============================================
# TAB 1: DASHBOARD
# ============================================
with tab1:
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Penjualan per Marketplace")
        market_sales = df.groupby('sumber_marketplace')['total'].sum().reset_index()
        market_sales = market_sales.sort_values('total', ascending=False)
        
        fig = px.pie(
            market_sales, 
            values='total', 
            names='sumber_marketplace',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Tren 7 Hari Terakhir")
        end_dt = datetime.strptime(end_str, '%Y-%m-%d')
        start_trend = end_dt - timedelta(days=6)
        
        trend_df = df[df['tanggal'] >= start_trend].copy()
        trend_daily = trend_df.groupby(trend_df['tanggal'].dt.date)['total'].sum().reset_index()
        trend_daily.columns = ['tanggal', 'total']
        
        # Fill missing dates
        date_range = pd.date_range(start=start_trend.date(), end=end_dt.date(), freq='D')
        trend_complete = pd.DataFrame({'tanggal': date_range})
        trend_complete['tanggal'] = trend_complete['tanggal'].dt.date
        trend_complete = trend_complete.merge(trend_daily, on='tanggal', how='left').fillna(0)
        
        fig = px.line(
            trend_complete, 
            x='tanggal', 
            y='total',
            markers=True,
            labels={'total': 'Penjualan (Rp)', 'tanggal': 'Tanggal'}
        )
        fig.update_traces(line_color='#3b82f6', fill='tozeroy', fillcolor='rgba(59,130,246,0.1)')
        fig.update_layout(xaxis_tickformat='%d/%m', height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    # Status table
    st.subheader("📋 Jumlah Pesanan per Status")
    status_counts = df.groupby('status_normal')['no_pesanan'].nunique().reset_index()
    status_counts.columns = ['Status', 'Jumlah Pesanan']
    status_counts = status_counts.sort_values('Jumlah Pesanan', ascending=False)
    status_counts['Persentase'] = (status_counts['Jumlah Pesanan'] / status_counts['Jumlah Pesanan'].sum() * 100).round(1).astype(str) + '%'
    
    st.dataframe(status_counts, use_container_width=True, hide_index=True)
    
    # Gudang table
    st.subheader("🏭 Omzet per Gudang")
    gudang_sales = df.groupby('gudang_alias')['total'].sum().reset_index()
    gudang_sales.columns = ['Gudang', 'Total Omset']
    gudang_sales = gudang_sales.sort_values('Total Omset', ascending=False)
    gudang_sales['Persentase'] = (gudang_sales['Total Omset'] / gudang_sales['Total Omset'].sum() * 100).round(1).astype(str) + '%'
    gudang_sales['Total Omset'] = gudang_sales['Total Omset'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
    
    st.dataframe(gudang_sales, use_container_width=True, hide_index=True)
    
    # ROAS per marketplace
    st.subheader("💰 ROAS per Marketplace")
    roas_data = []
    for market in df['sumber_marketplace'].unique():
        penjualan = df[df['sumber_marketplace'] == market]['total'].sum()
        iklan = df_iklan[df_iklan['sumber_marketplace'] == market]['biaya_iklan'].sum() if not df_iklan.empty else 0
        
        roas_val = penjualan / iklan if iklan > 0 else (999 if penjualan > 0 else 0)
        acos = (iklan / penjualan * 100) if penjualan > 0 else 0
        
        roas_data.append({
            'Marketplace': market,
            'Penjualan': f"Rp {penjualan:,.0f}".replace(",", "."),
            'Biaya Iklan': f"Rp {iklan:,.0f}".replace(",", "."),
            'ROAS': f"{roas_val:.2f}x" if roas_val < 999 else "∞",
            'ACOS': f"{acos:.2f}%"
        })
    
    roas_df = pd.DataFrame(roas_data)
    st.dataframe(roas_df, use_container_width=True, hide_index=True)
    
    # Recent orders
    st.subheader("📝 Data Pesanan Terbaru (50)")
    recent = df.nlargest(50, 'tanggal')[['tanggal', 'sumber_marketplace', 'no_pesanan', 
                                          'status_normal', 'kategori', 'sku_alias', 
                                          'gudang_alias', 'total']].copy()
    recent['tanggal'] = recent['tanggal'].dt.strftime('%d/%m/%Y')
    recent['total'] = recent['total'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
    recent.columns = ['Tanggal', 'Marketplace', 'No. Pesanan', 'Status', 'Kategori', 'SKU', 'Gudang', 'Total']
    
    st.dataframe(recent, use_container_width=True, hide_index=True)

# ============================================
# TAB 2: ANALISIS KATEGORI
# ============================================
with tab2:
    st.header("📦 Analisis Kategori")
    
    # Aggregate
    kat_stats = df.groupby('kategori').agg({
        'total': 'sum',
        'qty': 'sum',
        'no_pesanan': 'nunique'
    }).reset_index()
    kat_stats.columns = ['Kategori', 'Total Penjualan', 'Total Qty', 'Total Pesanan']
    kat_stats = kat_stats.sort_values('Total Penjualan', ascending=False)
    
    # Summary cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Kategori", len(kat_stats))
    c2.metric("Total Penjualan", f"Rp {kat_stats['Total Penjualan'].sum():,.0f}".replace(",", "."))
    c3.metric("Total Qty", f"{kat_stats['Total Qty'].sum():,}".replace(",", "."))
    c4.metric("Total Pesanan", f"{kat_stats['Total Pesanan'].sum():,}".replace(",", "."))
    
    # Trend selector
    st.subheader("📈 Tren Penjualan Kategori")
    selected_kategori = st.selectbox(
        "Pilih Kategori untuk melihat tren:",
        options=kat_stats['Kategori'].tolist()
    )
    
    if selected_kategori:
        kat_trend = df[df['kategori'] == selected_kategori].groupby(
            df['tanggal'].dt.to_period('M')
        )['total'].sum().reset_index()
        kat_trend['tanggal'] = kat_trend['tanggal'].astype(str)
        
        fig = px.line(kat_trend, x='tanggal', y='total', markers=True,
                     title=f"Tren: {selected_kategori}",
                     labels={'total': 'Penjualan (Rp)', 'tanggal': 'Bulan'})
        fig.update_traces(line_color='#3b82f6')
        st.plotly_chart(fig, use_container_width=True)
    
    # Table
    st.subheader("📋 Semua Kategori")
    kat_stats['Persentase'] = (kat_stats['Total Penjualan'] / kat_stats['Total Penjualan'].sum() * 100).round(1).astype(str) + '%'
    kat_stats['Rata-rata/Pesanan'] = (kat_stats['Total Penjualan'] / kat_stats['Total Pesanan']).round(0)
    
    kat_stats['Total Penjualan'] = kat_stats['Total Penjualan'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
    kat_stats['Rata-rata/Pesanan'] = kat_stats['Rata-rata/Pesanan'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
    
    st.dataframe(
        kat_stats[['Kategori', 'Total Penjualan', 'Total Qty', 'Total Pesanan', 'Rata-rata/Pesanan', 'Persentase']],
        use_container_width=True,
        hide_index=True
    )
    
    # Export
    csv_kat = kat_stats.to_csv(index=False)
    st.download_button(
        label="📥 Export CSV Kategori",
        data=csv_kat,
        file_name=f"analisis_kategori_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# ============================================
# TAB 3: ANALISIS SKU
# ============================================
with tab3:
    st.header("🔖 Analisis SKU")
    
    # Filter & Search
    col1, col2 = st.columns([2, 1])
    with col1:
        search_sku = st.text_input("🔍 Cari SKU", placeholder="Ketik nama SKU...")
    with col2:
        filter_kategori = st.selectbox(
            "Filter Kategori",
            options=["Semua"] + df['kategori'].unique().tolist()
        )
    
    # Filter dataframe
    sku_filtered = df.copy()
    if search_sku:
        sku_filtered = sku_filtered[sku_filtered['sku_alias'].str.contains(search_sku, case=False, na=False)]
    if filter_kategori != "Semua":
        sku_filtered = sku_filtered[sku_filtered['kategori'] == filter_kategori]
    
    # SKU stats
    sku_stats = sku_filtered.groupby(['sku_alias', 'kategori']).agg({
        'total': 'sum',
        'qty': 'sum',
        'no_pesanan': 'nunique'
    }).reset_index()
    sku_stats.columns = ['SKU', 'Kategori', 'Total Penjualan', 'Total Qty', 'Total Pesanan']
    sku_stats = sku_stats.sort_values('Total Penjualan', ascending=False)
    
    # Summary cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total SKU", len(sku_stats))
    c2.metric("Total Penjualan", f"Rp {sku_stats['Total Penjualan'].sum():,.0f}".replace(",", "."))
    c3.metric("Total Qty", f"{sku_stats['Total Qty'].sum():,}".replace(",", "."))
    c4.metric("Total Pesanan", f"{sku_stats['Total Pesanan'].sum():,}".replace(",", "."))
    
    # Info filter
    st.caption(f"Menampilkan {len(sku_stats)} SKU (dari {df['sku_alias'].nunique()} total)")
    
    # Trend
    st.subheader("📈 Tren Penjualan SKU")
    if not sku_stats.empty:
        selected_sku = st.selectbox(
            "Pilih SKU untuk melihat tren:",
            options=sku_stats['SKU'].tolist()
        )
        
        if selected_sku:
            sku_trend = df[df['sku_alias'] == selected_sku].groupby(
                df['tanggal'].dt.to_period('M')
            )['total'].sum().reset_index()
            sku_trend['tanggal'] = sku_trend['tanggal'].astype(str)
            
            fig = px.line(sku_trend, x='tanggal', y='total', markers=True,
                         title=f"Tren: {selected_sku}",
                         labels={'total': 'Penjualan (Rp)', 'tanggal': 'Bulan'})
            fig.update_traces(line_color='#10b981')
            st.plotly_chart(fig, use_container_width=True)
    
    # Table
    st.subheader("📋 Semua SKU")
    if not sku_stats.empty:
        sku_stats['Rata-rata Harga'] = (sku_stats['Total Penjualan'] / sku_stats['Total Qty']).round(0)
        sku_stats['Persentase'] = (sku_stats['Total Penjualan'] / sku_stats['Total Penjualan'].sum() * 100).round(1).astype(str) + '%'
        
        sku_stats['Total Penjualan'] = sku_stats['Total Penjualan'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
        sku_stats['Rata-rata Harga'] = sku_stats['Rata-rata Harga'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
        
        st.dataframe(
            sku_stats[['SKU', 'Kategori', 'Total Penjualan', 'Total Qty', 'Total Pesanan', 'Rata-rata Harga', 'Persentase']],
            use_container_width=True,
            hide_index=True
        )
        
        # Detail modal
        if st.button("👁️ Lihat Detail SKU Teratas"):
            top_sku = sku_stats.iloc[0]['SKU']
            detail_data = df[df['sku_alias'] == top_sku]
            
            st.write(f"**Detail untuk SKU: {top_sku}**")
            
            # Per marketplace
            market_detail = detail_data.groupby('sumber_marketplace').agg({
                'total': 'sum',
                'qty': 'sum'
            }).reset_index()
            market_detail['total'] = market_detail['total'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            st.write("Distribusi per Marketplace:")
            st.dataframe(market_detail, hide_index=True, use_container_width=True)
            
            # Recent transactions
            recent_trans = detail_data.nlargest(10, 'tanggal')[['tanggal', 'no_pesanan', 'sumber_marketplace', 'qty', 'total', 'status_normal']]
            recent_trans['tanggal'] = recent_trans['tanggal'].dt.strftime('%d/%m/%Y')
            recent_trans['total'] = recent_trans['total'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            st.write("Transaksi Terbaru:")
            st.dataframe(recent_trans, hide_index=True, use_container_width=True)
        
        # Export
        csv_sku = sku_stats.to_csv(index=False)
        st.download_button(
            label="📥 Export CSV SKU",
            data=csv_sku,
            file_name=f"analisis_sku_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Tidak ada SKU yang cocok dengan filter")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.caption(f"🕐 Last updated: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | 🔒 Data dienkripsi & privat")
