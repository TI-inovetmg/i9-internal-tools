import logging
import pandas as pd
from decimal import Decimal, InvalidOperation
from django.db import transaction
from core.services.protheus_etl import ProtheusBaseETL
from engenharia.models import EstruturaProduto

logger = logging.getLogger(__name__)


class AnaliseProducaoETLService(ProtheusBaseETL):
    """
    Serviço de ETL para cruzamento de Estrutura (SG1) com Ordens de Produção (SC2).
    Herda do core para padronização.
    """

    # Define as tabelas que o ProtheusBaseETL deve buscar no SFTP
    ARQUIVOS_ALVO = ["sg10101.sdb", "sb10101.sdb", "sc20101.sdb"]

    # Prefixos Inteligentes do Negócio (Smart Part Numbers) - Hardcode pois o protheus é limitado!!!!!!
    PREFIXO_VO = '1185'
    PREFIXO_PAI = '1180'
    PREFIXO_FILHO = '1160'

    @classmethod
    def transformar_e_salvar(cls, dados_limpos: dict):
        """Implementação obrigatória do Template Method do ProtheusBaseETL."""
        logger.info("[ENGENHARIA] Iniciando processamento de Análise de Produção...")

        df_processado = cls._processar_analise(dados_limpos)

        cls._salvar_no_banco(df_processado)

        logger.info("[ENGENHARIA] ETL finalizado com sucesso.")
        return True


    @classmethod
    def _processar_analise(cls, dados_brutos: dict) -> pd.DataFrame:
        """Regra de negócio pura e vetorizada do Pandas."""
        df_sg1 = dados_brutos['sg1'].copy()
        df_sb1 = dados_brutos['sb1'].copy()
        df_sc2 = dados_brutos['sc2'].copy()

        # PREPARAÇÃO DOS DADOS (Cadastro e OPs)
        df_sb1_mini = df_sb1[['B1_COD', 'B1_DESC']].drop_duplicates(subset='B1_COD')

        # Agrupamento de OPs (SC2) - soma a quantidade emitida em OP para o produto
        df_sc2['C2_QUANT'] = pd.to_numeric(df_sc2['C2_QUANT'], errors='coerce').fillna(0)
        df_ops_agrupadas = df_sc2.groupby('C2_PRODUTO')['C2_QUANT'].sum().reset_index()
        df_ops_agrupadas.rename(columns={'C2_QUANT': 'QTD_EM_OP'}, inplace=True)

        # ACHATAMENTO DA ESTRUTURA (VO -> PAI -> FILHO)
        df_vo = df_sg1[df_sg1['G1_COD'].str.startswith(cls.PREFIXO_VO)].copy()
        df_vo.rename(columns={'G1_COD': 'COD_VO', 'G1_COMP': 'COD_PAI', 'G1_QUANT': 'QTD_PAI'}, inplace=True)

        df_pai = df_sg1[df_sg1['G1_COD'].str.startswith(cls.PREFIXO_PAI)].copy()
        df_pai.rename(columns={'G1_COD': 'BUSCA_PAI', 'G1_COMP': 'COD_FILHO', 'G1_QUANT': 'QTD_FILHO'}, inplace=True)

        df_estrutura = pd.merge(df_vo, df_pai, how='inner', left_on='COD_PAI', right_on='BUSCA_PAI')

        # Multiplicador de Necessidade Real (USAMOS QUANTIDADE PAI * QUANTIDADE FILHO) ||| - 2 ELEVADOR * 32 GOMOS = PRECISA DE 64 GOMOS
        df_estrutura['QTD_PAI'] = pd.to_numeric(df_estrutura['QTD_PAI'], errors='coerce').fillna(1)
        df_estrutura['QTD_FILHO'] = pd.to_numeric(df_estrutura['QTD_FILHO'], errors='coerce').fillna(0)
        df_estrutura['NECESSIDADE_REAL_FILHO'] = df_estrutura['QTD_PAI'] * df_estrutura['QTD_FILHO']


        # O CRUZAMENTO FINAL COM A PRODUÇÃO
        logger.info(
            f"Amostra do cálculo: {df_estrutura[['COD_PAI', 'COD_FILHO', 'QTD_PAI', 'QTD_FILHO', 'NECESSIDADE_REAL_FILHO']].head(10)}")
        df_final = pd.merge(df_estrutura, df_ops_agrupadas, how='left', left_on='COD_FILHO', right_on='C2_PRODUTO')
        df_final['QTD_EM_OP'] = df_final['QTD_EM_OP'].fillna(0)

        df_final['FALTA_PRODUZIR'] = df_final['NECESSIDADE_REAL_FILHO'] - df_final['QTD_EM_OP']
        df_final['FALTA_PRODUZIR'] = df_final['FALTA_PRODUZIR'].apply(lambda x: x if x > 0 else 0)

        # MELHORAMENTO DE DESCRIÇÕES (SB1)
        df_final = pd.merge(df_final, df_sb1_mini, how='left', left_on='COD_VO', right_on='B1_COD')
        df_final.rename(columns={'B1_DESC': 'DESC_VO'}, inplace=True)

        df_final = pd.merge(df_final, df_sb1_mini, how='left', left_on='COD_PAI', right_on='B1_COD')
        df_final.rename(columns={'B1_DESC': 'DESC_PAI'}, inplace=True)


        df_final = pd.merge(df_final, df_sb1_mini, how='left', left_on='COD_FILHO', right_on='B1_COD')
        df_final.rename(columns={'B1_DESC': 'DESC_FILHO'}, inplace=True)

        # Limpeza
        df_final.drop(columns=['B1_COD_x', 'B1_COD_y', 'BUSCA_PAI', 'C2_PRODUTO'], errors='ignore', inplace=True)
        df_final.fillna('', inplace=True)

        return df_final


    @classmethod
    def _salvar_no_banco(cls, df: pd.DataFrame):
        logger.info("[ENGENHARIA] Convertendo DataFrame para registros ORM (Decimal Safe)...")

        # Vetorização para dicionários
        records = df.to_dict('records')

        # Utilitário local para garantir o cast seguro para o DecimalField
        def limpa_decimal(val):
            try:
                # Se for nulo no pandas ou string vazia, retorna 0.0
                if pd.isna(val) or val == '':
                    return Decimal('0.0')
                # Força para string antes de virar Decimal para evitar lixo de ponto flutuante
                return Decimal(str(val))
            except (InvalidOperation, ValueError, TypeError):
                return Decimal('0.0')

        # 3. List Comprehension de alta performance
        registros_orm = [
            EstruturaProduto(
                codigo_vo=str(r.get('COD_VO', '')).strip(),
                descricao_vo=str(r.get('DESC_VO', '')).strip(),

                codigo_pai=str(r.get('COD_PAI', '')).strip(),
                descricao_pai=str(r.get('DESC_PAI', '')).strip(),

                codigo_filho=str(r.get('COD_FILHO', '')).strip(),
                descricao_filho=str(r.get('DESC_FILHO', '')).strip(),

                quantidade_necessaria_filho=limpa_decimal(r.get('NECESSIDADE_REAL_FILHO')),
                quantidade_em_op=limpa_decimal(r.get('QTD_EM_OP')),
                falta_produzir=limpa_decimal(r.get('FALTA_PRODUZIR'))
            ) for r in records
        ]

        # Transação Atômica
        with transaction.atomic():
            logger.info("[ENGENHARIA] Realizando Full Refresh da Análise de Produção...")
            EstruturaProduto.objects.all().delete()
            EstruturaProduto.objects.bulk_create(registros_orm, batch_size=2000)
            logger.info(f"[ENGENHARIA] Foram persistidos {len(registros_orm)} componentes.")