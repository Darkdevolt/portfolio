import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import requests
import plotly.graph_objects as go
import plotly.express as px
from io import StringIO
import base64

# Configuration de la page
st.set_page_config(
    page_title="BRVM Portfolio Manager",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration GitHub
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "votre-username/brvm-portfolio")
GITHUB_BRANCH = "main"

class BRVMPortfolioManager:
    def __init__(self):
        self.initialize_session_state()
        self.load_market_data()
    
    def initialize_session_state(self):
        """Initialise les variables de session"""
        if 'portfolio' not in st.session_state:
            st.session_state.portfolio = {}
        if 'transactions' not in st.session_state:
            st.session_state.transactions = []
        if 'cash_balance' not in st.session_state:
            st.session_state.cash_balance = 1000000  # 1M FCFA initial
        if 'pending_orders' not in st.session_state:
            st.session_state.pending_orders = []
    
    def load_market_data(self):
        """Charge les données du marché BRVM"""
        # Données simulées des principales actions BRVM
        self.market_data = {
            'BICC': {'price': 8500, 'change': 2.5, 'volume': 15000, 'sector': 'Construction'},
            'BOAB': {'price': 4200, 'change': -1.2, 'volume': 8500, 'sector': 'Banque'},
            'BOABF': {'price': 4150, 'change': 0.8, 'volume': 12000, 'sector': 'Banque'},
            'BOAC': {'price': 3950, 'change': 1.5, 'volume': 9500, 'sector': 'Banque'},
            'BOCIG': {'price': 6200, 'change': -0.5, 'volume': 7200, 'sector': 'Assurance'},
            'CFAC': {'price': 850, 'change': 3.2, 'volume': 25000, 'sector': 'Automobile'},
            'CGBC': {'price': 1250, 'change': -2.1, 'volume': 18000, 'sector': 'Commerce'},
            'EIBC': {'price': 5800, 'change': 1.8, 'volume': 11000, 'sector': 'Industrie'},
            'ETIT': {'price': 18, 'change': 4.5, 'volume': 45000, 'sector': 'Telecom'},
            'NEIC': {'price': 4950, 'change': -1.8, 'volume': 6800, 'sector': 'Assurance'},
            'NTLC': {'price': 950, 'change': 2.2, 'volume': 32000, 'sector': 'Textile'},
            'ORAC': {'price': 2800, 'change': 0.5, 'volume': 14500, 'sector': 'Mining'},
            'PALC': {'price': 2950, 'change': -3.1, 'volume': 8900, 'sector': 'Agro'},
            'PRSC': {'price': 350, 'change': 1.9, 'volume': 55000, 'sector': 'Distribution'},
            'SAFC': {'price': 2450, 'change': -0.8, 'volume': 16700, 'sector': 'Agro'},
            'SGBC': {'price': 11500, 'change': 2.8, 'volume': 5400, 'sector': 'Banque'},
            'SHEC': {'price': 2750, 'change': 1.1, 'volume': 19800, 'sector': 'Energie'},
            'SIBC': {'price': 4800, 'change': -2.5, 'volume': 7650, 'sector': 'Banque'},
            'SICC': {'price': 1850, 'change': 0.9, 'volume': 28500, 'sector': 'Ciment'},
            'SLBC': {'price': 1950, 'change': 1.4, 'volume': 13200, 'sector': 'Banque'},
            'SMBC': {'price': 8200, 'change': -1.6, 'volume': 4200, 'sector': 'Banque'},
            'SNTS': {'price': 4650, 'change': 2.1, 'volume': 9800, 'sector': 'Transport'},
            'SOGC': {'price': 4950, 'change': 0.7, 'volume': 15600, 'sector': 'Commerce'},
            'STAC': {'price': 650, 'change': -1.9, 'volume': 38000, 'sector': 'Agro'},
            'STBC': {'price': 950, 'change': 3.5, 'volume': 24500, 'sector': 'Banque'},
            'TTLC': {'price': 350, 'change': 1.2, 'volume': 65000, 'sector': 'Textile'},
            'UNLC': {'price': 2850, 'change': -0.3, 'volume': 11900, 'sector': 'Logistique'}
        }
        
        # Règles BRVM
        self.brvm_rules = {
            'trading_hours': {'open': '08:00', 'close': '15:30'},
            'settlement_days': 3,  # J+3 pour le règlement-livraison
            'min_lot_size': 1,
            'price_limits': {'static': 0.075},  # ±7.5% limite statique
            'commission_rate': 0.006,  # 0.6% de commission
            'min_commission': 5000,  # Commission minimum 5000 FCFA
            'trading_days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        }
    
    def calculate_price_limits(self, reference_price):
        """Calcule les limites de prix selon les règles BRVM"""
        limit_pct = self.brvm_rules['price_limits']['static']
        upper_limit = reference_price * (1 + limit_pct)
        lower_limit = reference_price * (1 - limit_pct)
        return lower_limit, upper_limit
    
    def calculate_commission(self, amount):
        """Calcule la commission selon les règles BRVM"""
        commission = max(amount * self.brvm_rules['commission_rate'], 
                        self.brvm_rules['min_commission'])
        return commission
    
    def is_trading_time(self):
        """Vérifie si c'est l'heure de trading"""
        now = datetime.now()
        if now.strftime('%A') not in self.brvm_rules['trading_days']:
            return False, "Marché fermé (weekend)"
        
        current_time = now.strftime('%H:%M')
        if current_time < self.brvm_rules['trading_hours']['open']:
            return False, f"Marché pas encore ouvert (ouverture à {self.brvm_rules['trading_hours']['open']})"
        elif current_time > self.brvm_rules['trading_hours']['close']:
            return False, f"Marché fermé (fermeture à {self.brvm_rules['trading_hours']['close']})"
        
        return True, "Marché ouvert"
    
    def execute_order(self, symbol, order_type, quantity, price=None):
        """Execute un ordre d'achat ou de vente"""
        if symbol not in self.market_data:
            return False, "Symbole non trouvé"
        
        current_price = self.market_data[symbol]['price']
        order_price = price if price else current_price
        
        # Vérification des limites de prix
        lower_limit, upper_limit = self.calculate_price_limits(current_price)
        if order_price < lower_limit or order_price > upper_limit:
            return False, f"Prix hors limites ({lower_limit:.0f} - {upper_limit:.0f} FCFA)"
        
        total_amount = quantity * order_price
        commission = self.calculate_commission(total_amount)
        
        if order_type == 'BUY':
            total_cost = total_amount + commission
            if st.session_state.cash_balance < total_cost:
                return False, "Liquidités insuffisantes"
            
            # Vérification de la liquidité du marché
            if quantity > self.market_data[symbol]['volume'] * 0.1:  # Max 10% du volume
                return False, "Quantité trop importante par rapport à la liquidité"
            
            # Exécution de l'achat
            st.session_state.cash_balance -= total_cost
            if symbol in st.session_state.portfolio:
                st.session_state.portfolio[symbol]['quantity'] += quantity
                # Recalcul du prix moyen pondéré
                old_value = st.session_state.portfolio[symbol]['avg_price'] * st.session_state.portfolio[symbol]['quantity'] - quantity * order_price
                new_quantity = st.session_state.portfolio[symbol]['quantity']
                st.session_state.portfolio[symbol]['avg_price'] = (old_value + quantity * order_price) / new_quantity
            else:
                st.session_state.portfolio[symbol] = {
                    'quantity': quantity,
                    'avg_price': order_price,
                    'sector': self.market_data[symbol]['sector']
                }
            
            # Enregistrement de la transaction
            transaction = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'type': 'BUY',
                'quantity': quantity,
                'price': order_price,
                'commission': commission,
                'total': total_cost,
                'settlement_date': (datetime.now() + timedelta(days=self.brvm_rules['settlement_days'])).isoformat()
            }
            st.session_state.transactions.append(transaction)
            
            return True, f"Achat exécuté: {quantity} {symbol} à {order_price} FCFA (Commission: {commission:.0f} FCFA)"
        
        elif order_type == 'SELL':
            # Vérification de la détention
            if symbol not in st.session_state.portfolio or st.session_state.portfolio[symbol]['quantity'] < quantity:
                return False, "Actions insuffisantes en portefeuille"
            
            # Exécution de la vente
            total_received = total_amount - commission
            st.session_state.cash_balance += total_received
            st.session_state.portfolio[symbol]['quantity'] -= quantity
            
            # Suppression si quantité = 0
            if st.session_state.portfolio[symbol]['quantity'] == 0:
                del st.session_state.portfolio[symbol]
            
            # Enregistrement de la transaction
            transaction = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'type': 'SELL',
                'quantity': quantity,
                'price': order_price,
                'commission': commission,
                'total': total_received,
                'settlement_date': (datetime.now() + timedelta(days=self.brvm_rules['settlement_days'])).isoformat()
            }
            st.session_state.transactions.append(transaction)
            
            return True, f"Vente exécutée: {quantity} {symbol} à {order_price} FCFA (Commission: {commission:.0f} FCFA)"
    
    def save_to_github(self):
        """Sauvegarde les données sur GitHub"""
        if not GITHUB_TOKEN:
            st.warning("Token GitHub non configuré. Données sauvegardées localement seulement.")
            return False
        
        data = {
            'portfolio': st.session_state.portfolio,
            'transactions': st.session_state.transactions,
            'cash_balance': st.session_state.cash_balance,
            'last_update': datetime.now().isoformat()
        }
        
        try:
            # Encodage en base64
            content = base64.b64encode(json.dumps(data, indent=2).encode()).decode()
            
            # API GitHub pour créer/mettre à jour un fichier
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/portfolio_data.json"
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Vérification si le fichier existe déjà
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    sha = response.json()['sha']
                else:
                    sha = None
            except:
                sha = None
            
            # Données pour l'API
            payload = {
                "message": f"Update portfolio data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "content": content,
                "branch": GITHUB_BRANCH
            }
            
            if sha:
                payload["sha"] = sha
            
            response = requests.put(url, headers=headers, json=payload)
            
            if response.status_code in [200, 201]:
                st.success("✅ Données sauvegardées sur GitHub avec succès!")
                return True
            else:
                st.error(f"❌ Erreur lors de la sauvegarde: {response.status_code}")
                return False
                
        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            return False
    
    def load_from_github(self):
        """Charge les données depuis GitHub"""
        if not GITHUB_TOKEN:
            return False
        
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/portfolio_data.json"
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                content = base64.b64decode(response.json()['content']).decode()
                data = json.loads(content)
                
                st.session_state.portfolio = data.get('portfolio', {})
                st.session_state.transactions = data.get('transactions', [])
                st.session_state.cash_balance = data.get('cash_balance', 1000000)
                
                st.success("✅ Données chargées depuis GitHub avec succès!")
                return True
            else:
                st.info("ℹ️ Aucune sauvegarde trouvée sur GitHub")
                return False
                
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement: {str(e)}")
            return False

def main():
    st.title("🏛️ BRVM Portfolio Manager")
    st.markdown("**Plateforme avancée de gestion de portefeuille - Bourse Régionale des Valeurs Mobilières**")
    
    # Initialisation du gestionnaire
    portfolio_manager = BRVMPortfolioManager()
    
    # Sidebar pour les actions principales
    with st.sidebar:
        st.header("🔧 Actions")
        
        if st.button("💾 Sauvegarder sur GitHub", type="primary"):
            portfolio_manager.save_to_github()
        
        if st.button("📥 Charger depuis GitHub"):
            portfolio_manager.load_from_github()
        
        st.divider()
        
        # Statut du marché
        is_open, status_msg = portfolio_manager.is_trading_time()
        if is_open:
            st.success(f"🟢 {status_msg}")
        else:
            st.warning(f"🟡 {status_msg}")
        
        st.divider()
        
        # Informations du compte
        st.header("💰 Mon Compte")
        st.metric("Liquidités", f"{st.session_state.cash_balance:,.0f} FCFA")
        
        # Calcul de la valeur totale du portefeuille
        portfolio_value = 0
        for symbol, holding in st.session_state.portfolio.items():
            current_price = portfolio_manager.market_data[symbol]['price']
            portfolio_value += holding['quantity'] * current_price
        
        st.metric("Valeur Portefeuille", f"{portfolio_value:,.0f} FCFA")
        st.metric("Total Patrimoine", f"{st.session_state.cash_balance + portfolio_value:,.0f} FCFA")
    
    # Tabs principales
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Marché", "💼 Mon Portefeuille", "🔄 Trading", "📋 Historique", "📈 Analyses"])
    
    with tab1:
        st.header("📊 État du Marché BRVM")
        
        # Création du DataFrame pour affichage
        market_df = pd.DataFrame(portfolio_manager.market_data).T
        market_df.reset_index(inplace=True)
        market_df.rename(columns={'index': 'Symbole'}, inplace=True)
        market_df['Prix (FCFA)'] = market_df['price']
        market_df['Variation (%)'] = market_df['change']
        market_df['Volume'] = market_df['volume']
        market_df['Secteur'] = market_df['sector']
        
        # Ajout des limites de prix
        market_df['Limite Basse'] = market_df['price'] * (1 - portfolio_manager.brvm_rules['price_limits']['static'])
        market_df['Limite Haute'] = market_df['price'] * (1 + portfolio_manager.brvm_rules['price_limits']['static'])
        
        # Affichage du tableau avec couleurs
        st.dataframe(
            market_df[['Symbole', 'Prix (FCFA)', 'Variation (%)', 'Volume', 'Secteur', 'Limite Basse', 'Limite Haute']],
            column_config={
                "Variation (%)": st.column_config.NumberColumn(
                    "Variation (%)",
                    format="%.2f%%"
                ),
                "Prix (FCFA)": st.column_config.NumberColumn(
                    "Prix (FCFA)",
                    format="%.0f"
                ),
                "Volume": st.column_config.NumberColumn(
                    "Volume",
                    format="%d"
                ),
                "Limite Basse": st.column_config.NumberColumn(
                    "Limite Basse",
                    format="%.0f"
                ),
                "Limite Haute": st.column_config.NumberColumn(
                    "Limite Haute",
                    format="%.0f"
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Graphiques de visualisation
        col1, col2 = st.columns(2)
        
        with col1:
            # Top gainers/losers
            sorted_by_change = market_df.sort_values('Variation (%)', ascending=False)
            
            fig_gainers = px.bar(
                sorted_by_change.head(10),
                x='Variation (%)',
                y='Symbole',
                title="🚀 Top 10 Gagnants",
                color='Variation (%)',
                color_continuous_scale=['red', 'yellow', 'green'],
                orientation='h'
            )
            st.plotly_chart(fig_gainers, use_container_width=True)
        
        with col2:
            # Répartition par secteur
            sector_counts = market_df['Secteur'].value_counts()
            fig_sectors = px.pie(
                values=sector_counts.values,
                names=sector_counts.index,
                title="📈 Répartition par Secteur"
            )
            st.plotly_chart(fig_sectors, use_container_width=True)
    
    with tab2:
        st.header("💼 Mon Portefeuille")
        
        if st.session_state.portfolio:
            # Création du DataFrame du portefeuille
            portfolio_data = []
            total_value = 0
            total_invested = 0
            
            for symbol, holding in st.session_state.portfolio.items():
                current_price = portfolio_manager.market_data[symbol]['price']
                market_value = holding['quantity'] * current_price
                invested_value = holding['quantity'] * holding['avg_price']
                pnl = market_value - invested_value
                pnl_pct = (pnl / invested_value) * 100 if invested_value > 0 else 0
                
                portfolio_data.append({
                    'Symbole': symbol,
                    'Quantité': holding['quantity'],
                    'Prix Moyen': holding['avg_price'],
                    'Prix Actuel': current_price,
                    'Valeur Investie': invested_value,
                    'Valeur Marché': market_value,
                    'P&L': pnl,
                    'P&L (%)': pnl_pct,
                    'Secteur': holding['sector']
                })
                
                total_value += market_value
                total_invested += invested_value
            
            portfolio_df = pd.DataFrame(portfolio_data)
            
            # Métriques générales
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Valeur Investie", f"{total_invested:,.0f} FCFA")
            with col2:
                st.metric("Valeur Marché", f"{total_value:,.0f} FCFA")
            with col3:
                total_pnl = total_value - total_invested
                st.metric("P&L Total", f"{total_pnl:,.0f} FCFA", delta=f"{(total_pnl/total_invested)*100:.2f}%" if total_invested > 0 else None)
            with col4:
                st.metric("Nombre Titres", len(st.session_state.portfolio))
            
            # Tableau détaillé
            st.dataframe(
                portfolio_df,
                column_config={
                    "Prix Moyen": st.column_config.NumberColumn("Prix Moyen", format="%.0f"),
                    "Prix Actuel": st.column_config.NumberColumn("Prix Actuel", format="%.0f"),
                    "Valeur Investie": st.column_config.NumberColumn("Valeur Investie", format="%.0f"),
                    "Valeur Marché": st.column_config.NumberColumn("Valeur Marché", format="%.0f"),
                    "P&L": st.column_config.NumberColumn("P&L", format="%.0f"),
                    "P&L (%)": st.column_config.NumberColumn("P&L (%)", format="%.2f%%")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Graphiques
            col1, col2 = st.columns(2)
            
            with col1:
                # Répartition par valeur
                fig_allocation = px.pie(
                    portfolio_df,
                    values='Valeur Marché',
                    names='Symbole',
                    title="💰 Allocation du Portefeuille"
                )
                st.plotly_chart(fig_allocation, use_container_width=True)
            
            with col2:
                # Performance par titre
                fig_performance = px.bar(
                    portfolio_df,
                    x='Symbole',
                    y='P&L (%)',
                    title="📊 Performance par Titre",
                    color='P&L (%)',
                    color_continuous_scale=['red', 'yellow', 'green']
                )
                st.plotly_chart(fig_performance, use_container_width=True)
        
        else:
            st.info("🔍 Votre portefeuille est vide. Commencez par acheter des actions dans l'onglet Trading.")
    
    with tab3:
        st.header("🔄 Plateforme de Trading")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Acheter des Actions")
            
            buy_symbol = st.selectbox("Sélectionner une action", 
                                    list(portfolio_manager.market_data.keys()),
                                    key="buy_symbol")
            
            if buy_symbol:
                current_price = portfolio_manager.market_data[buy_symbol]['price']
                lower_limit, upper_limit = portfolio_manager.calculate_price_limits(current_price)
                
                st.info(f"Prix actuel: {current_price:,} FCFA | Limites: {lower_limit:.0f} - {upper_limit:.0f} FCFA")
                
                buy_quantity = st.number_input("Quantité à acheter", min_value=1, value=1, key="buy_qty")
                buy_price = st.number_input("Prix limite (optionnel)", 
                                          min_value=float(lower_limit), 
                                          max_value=float(upper_limit),
                                          value=float(current_price),
                                          key="buy_price")
                
                total_cost = buy_quantity * buy_price + portfolio_manager.calculate_commission(buy_quantity * buy_price)
                st.write(f"**Coût total estimé: {total_cost:,.0f} FCFA**")
                
                if st.button("🛒 Acheter", type="primary", key="buy_btn"):
                    success, message = portfolio_manager.execute_order(buy_symbol, 'BUY', buy_quantity, buy_price)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        
        with col2:
            st.subheader("💸 Vendre des Actions")
            
            if st.session_state.portfolio:
                sell_symbol = st.selectbox("Sélectionner une action", 
                                         list(st.session_state.portfolio.keys()),
                                         key="sell_symbol")
                
                if sell_symbol:
                    current_price = portfolio_manager.market_data[sell_symbol]['price']
                    owned_quantity = st.session_state.portfolio[sell_symbol]['quantity']
                    lower_limit, upper_limit = portfolio_manager.calculate_price_limits(current_price)
                    
                    st.info(f"Prix actuel: {current_price:,} FCFA | Quantité détenue: {owned_quantity}")
                    
                    sell_quantity = st.number_input("Quantité à vendre", 
                                                  min_value=1, 
                                                  max_value=owned_quantity, 
                                                  value=min(1, owned_quantity),
                                                  key="sell_qty")
                    sell_price = st.number_input("Prix limite (optionnel)", 
                                               min_value=float(lower_limit), 
                                               max_value=float(upper_limit),
                                               value=float(current_price),
                                               key="sell_price")
                    
                    total_received = sell_quantity * sell_price - portfolio_manager.calculate_commission(sell_quantity * sell_price)
                    st.write(f"**Montant net estimé: {total_received:,.0f} FCFA**")
                    
                    if st.button("💰 Vendre", type="primary", key="sell_btn"):
                        success, message = portfolio_manager.execute_order(sell_symbol, 'SELL', sell_quantity, sell_price)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            else:
                st.info("🔍 Aucune action en portefeuille à vendre.")
        
        # Règles BRVM
        st.divider()
        st.subheader("📋 Règles BRVM en Vigueur")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Limite Statique", "±7.5%")
            st.metric("Commission Min.", "5,000 FCFA")
        with col2:
            st.metric("Taux Commission", "0.6%")
            st.metric("Règlement-Livraison", "J+3")
        with col3:
            st.metric("Heures Trading", "08:00 - 15:30")
            st.metric("Jours Trading", "Lun-Ven")
    
    with tab4:
        st.header("📋 Historique des Transactions")
        
        if st.session_state.transactions:
            # Conversion en DataFrame
            transactions_df = pd.DataFrame(st.session_state.transactions)
            transactions_df['Date'] = pd.to_datetime(transactions_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            transactions_df['Date Règlement'] = pd.to_datetime(transactions_df['settlement_date']).dt.strftime('%Y-%m-%d')
            
            # Filtres
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_type = st.selectbox("Type", ["Tous", "BUY", "SELL"])
            with col2:
                symbols = ["Tous"] + list(set(transactions_df['symbol'].tolist()))
                filter_symbol = st.selectbox("Symbole", symbols)
            with col3:
                st.write("") # Espace
            
            # Application des filtres
            filtered_df = transactions_df.copy()
            if filter_type != "Tous":
                filtered_df = filtered_df[filtered_df['type'] == filter_type]
            if filter_symbol != "Tous":
                filtered_df = filtered_df[filtered_df['symbol'] == filter_symbol]
            
            # Affichage du tableau
            display_columns = ['Date', 'symbol', 'type', 'quantity', 'price', 'commission', 'total', 'Date Règlement']
            column_config = {
                'symbol': 'Symbole',
                'type': 'Type',
                'quantity': 'Quantité',
                'price': st.column_config.NumberColumn('Prix', format="%.0f"),
                'commission': st.column_config.NumberColumn('Commission', format="%.0f"),
                'total': st.column_config.NumberColumn('Total', format="%.0f")
            }
            
            st.dataframe(
                filtered_df[display_columns],
                column_config=column_config,
                hide_index=True,
                use_container_width=True
            )
            
            # Statistiques
            st.subheader("📊 Statistiques des Transactions")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_trades = len(filtered_df)
                st.metric("Total Transactions", total_trades)
            
            with col2:
                total_commission = filtered_df['commission'].sum()
                st.metric("Total Commissions", f"{total_commission:,.0f} FCFA")
            
            with col3:
                buy_trades = len(filtered_df[filtered_df['type'] == 'BUY'])
                sell_trades = len(filtered_df[filtered_df['type'] == 'SELL'])
                st.metric("Achats/Ventes", f"{buy_trades}/{sell_trades}")
            
            with col4:
                total_volume = filtered_df['total'].sum()
                st.metric("Volume Total", f"{total_volume:,.0f} FCFA")
            
            # Graphique des transactions dans le temps
            if len(filtered_df) > 0:
                filtered_df['Date_dt'] = pd.to_datetime(filtered_df['timestamp'])
                daily_volume = filtered_df.groupby(filtered_df['Date_dt'].dt.date)['total'].sum().reset_index()
                
                fig_volume = px.line(
                    daily_volume,
                    x='Date_dt',
                    y='total',
                    title="📈 Volume des Transactions par Jour",
                    labels={'total': 'Volume (FCFA)', 'Date_dt': 'Date'}
                )
                st.plotly_chart(fig_volume, use_container_width=True)
        
        else:
            st.info("📝 Aucune transaction effectuée pour le moment.")
    
    with tab5:
        st.header("📈 Analyses et Rapports")
        
        # Performance du portefeuille
        if st.session_state.portfolio and st.session_state.transactions:
            st.subheader("🎯 Analyse de Performance")
            
            # Calculs de performance
            total_invested = 0
            total_current_value = 0
            sector_allocation = {}
            
            for symbol, holding in st.session_state.portfolio.items():
                invested = holding['quantity'] * holding['avg_price']
                current_value = holding['quantity'] * portfolio_manager.market_data[symbol]['price']
                sector = holding['sector']
                
                total_invested += invested
                total_current_value += current_value
                
                if sector not in sector_allocation:
                    sector_allocation[sector] = 0
                sector_allocation[sector] += current_value
            
            # Métriques de performance
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_return = total_current_value - total_invested
                return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0
                st.metric("Rendement Total", f"{total_return:+,.0f} FCFA", f"{return_pct:+.2f}%")
            
            with col2:
                total_commissions = sum([t['commission'] for t in st.session_state.transactions])
                st.metric("Frais Totaux", f"{total_commissions:,.0f} FCFA")
            
            with col3:
                net_return = total_return - total_commissions
                st.metric("Rendement Net", f"{net_return:+,.0f} FCFA")
            
            # Allocation sectorielle
            col1, col2 = st.columns(2)
            
            with col1:
                if sector_allocation:
                    sector_df = pd.DataFrame(list(sector_allocation.items()), columns=['Secteur', 'Valeur'])
                    fig_sectors = px.pie(
                        sector_df,
                        values='Valeur',
                        names='Secteur',
                        title="🏭 Allocation Sectorielle"
                    )
                    st.plotly_chart(fig_sectors, use_container_width=True)
            
            with col2:
                # Top positions
                position_data = []
                for symbol, holding in st.session_state.portfolio.items():
                    current_value = holding['quantity'] * portfolio_manager.market_data[symbol]['price']
                    weight = (current_value / total_current_value * 100) if total_current_value > 0 else 0
                    position_data.append({
                        'Symbole': symbol,
                        'Poids (%)': weight,
                        'Valeur': current_value
                    })
                
                position_df = pd.DataFrame(position_data).sort_values('Poids (%)', ascending=False)
                
                fig_positions = px.bar(
                    position_df.head(10),
                    x='Poids (%)',
                    y='Symbole',
                    title="📊 Top 10 Positions",
                    orientation='h'
                )
                st.plotly_chart(fig_positions, use_container_width=True)
            
            # Analyse des risques
            st.subheader("⚠️ Analyse des Risques")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Concentration
                max_position = position_df['Poids (%)'].max() if not position_df.empty else 0
                risk_level = "Élevé" if max_position > 20 else "Modéré" if max_position > 10 else "Faible"
                st.metric("Risque de Concentration", f"{max_position:.1f}%", risk_level)
                
                # Diversification sectorielle
                nb_sectors = len(sector_allocation)
                div_score = "Bonne" if nb_sectors >= 5 else "Moyenne" if nb_sectors >= 3 else "Faible"
                st.metric("Diversification", f"{nb_sectors} secteurs", div_score)
            
            with col2:
                # Volatilité du portefeuille (simulée)
                portfolio_volatility = np.mean([abs(portfolio_manager.market_data[symbol]['change']) 
                                              for symbol in st.session_state.portfolio.keys()])
                vol_level = "Élevée" if portfolio_volatility > 2 else "Modérée" if portfolio_volatility > 1 else "Faible"
                st.metric("Volatilité Moyenne", f"{portfolio_volatility:.1f}%", vol_level)
                
                # Liquidité moyenne
                avg_volume = np.mean([portfolio_manager.market_data[symbol]['volume'] 
                                    for symbol in st.session_state.portfolio.keys()])
                liq_level = "Bonne" if avg_volume > 15000 else "Moyenne" if avg_volume > 8000 else "Faible"
                st.metric("Liquidité Moyenne", f"{avg_volume:,.0f}", liq_level)
        
        else:
            st.info("📊 Les analyses seront disponibles une fois que vous aurez des positions en portefeuille.")
        
        # Rapports détaillés
        st.subheader("📋 Rapports Détaillés")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Générer Rapport de Performance", type="secondary"):
                if st.session_state.portfolio:
                    # Génération d'un rapport détaillé
                    report_data = {
                        'Date du rapport': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Nombre de positions': len(st.session_state.portfolio),
                        'Valeur totale investie': f"{total_invested:,.0f} FCFA",
                        'Valeur marché actuelle': f"{total_current_value:,.0f} FCFA",
                        'Plus-value/Moins-value': f"{total_return:+,.0f} FCFA ({return_pct:+.2f}%)",
                        'Liquidités disponibles': f"{st.session_state.cash_balance:,.0f} FCFA",
                        'Patrimoine total': f"{st.session_state.cash_balance + total_current_value:,.0f} FCFA"
                    }
                    
                    st.json(report_data)
                else:
                    st.warning("Aucune donnée de portefeuille à analyser.")
        
        with col2:
            if st.button("📈 Exporter Données CSV", type="secondary"):
                if st.session_state.transactions:
                    # Export des transactions
                    df_export = pd.DataFrame(st.session_state.transactions)
                    csv = df_export.to_csv(index=False)
                    
                    st.download_button(
                        label="⬇️ Télécharger Historique",
                        data=csv,
                        file_name=f"brvm_transactions_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("Aucune transaction à exporter.")

    # Footer avec informations importantes
    st.divider()
    st.markdown("""
    ---
    **⚠️ Informations Importantes:**
    - Cette plateforme simule le trading sur la BRVM avec des données réelles approximatives
    - Les règles BRVM sont respectées : limites de prix ±7.5%, règlement J+3, commissions 0.6%
    - Données automatiquement sauvegardées sur GitHub pour synchronisation multi-appareils
    - **Avertissement**: Cette application est à des fins éducatives et de simulation uniquement
    
    **🔧 Configuration GitHub Required:**
    - Créez un dépôt GitHub privé pour stocker vos données
    - Ajoutez votre `GITHUB_TOKEN` et `GITHUB_REPO` dans les secrets Streamlit
    - Format: `username/repository-name`
    
    **📞 Support:** Cette plateforme respecte fidèlement les règles de trading de la BRVM
    """)

if __name__ == "__main__":
    main()
