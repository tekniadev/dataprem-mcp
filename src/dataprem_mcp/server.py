"""DataPrem MCP Server.

Exposes Spanish public data sources (Catastro, BORME, Licitaciones,
Subvenciones) as MCP tools for AI agents. All four are wired against the real
DataPrem REST API (`api.dataprem.com`) — see README for the status table.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from dataprem_mcp import catalogue
from dataprem_mcp.api_client import DatapremApiClient

mcp = MCPServer("DataPrem")

# The names this server can actually run. The catalogue may reword them; it may
# not add to them, because a tool with no handler here is one the model will
# pick and then fail to use.
IMPLEMENTED = {
    "dataprem_catastro_lookup",
    "dataprem_borme_search",
    "dataprem_tenders_search",
    "dataprem_subsidies_search",
}

DESCRIPTIONS = catalogue.descriptions(IMPLEMENTED)


# ---------------------------------------------------------------------------
# Tool: Catastro — REAL (DataPrem API, no stub)
# ---------------------------------------------------------------------------


@mcp.tool(description=DESCRIPTIONS["dataprem_catastro_lookup"])
def dataprem_catastro_lookup(
    refcat: str | None = None,
    address: str | None = None,
    city: str | None = None,
    province: str | None = None,
) -> dict[str, Any]:
    """Consulta datos catastrales de un inmueble en el Catastro español.

    Provee uno de los dos modos de búsqueda:

    * **Por referencia catastral** — pasar `refcat` (14, 18 o 20 caracteres).
    * **Por dirección** — pasar `address` + `city`, opcionalmente `province`.

    Devuelve la ficha catastral normalizada: clase, uso, superficies, año de
    construcción, dirección con códigos INE, y el desglose de construcciones
    (`constructions[]`) con planta, puerta y superficie por componente.

    El endpoint **no expone titular** (datos personales): el SOAP libre del
    Catastro no lo facilita y la API pública lo descarta por LOPD/GDPR.
    Consulta autorizada con certificado del titular en pipeline futuro.

    Args:
        refcat: Referencia catastral del inmueble.
        address: Dirección literal (tipo + nombre + número).
        city: Municipio.
        province: Provincia (opcional).
    """
    client = DatapremApiClient()
    return client.get_catastro_property(
        refcat=refcat, address=address, city=city, province=province
    )


# ---------------------------------------------------------------------------
# Tool: BORME — answered by the API with data since 2009
# ---------------------------------------------------------------------------


@mcp.tool(description=DESCRIPTIONS["dataprem_borme_search"])
def dataprem_borme_search(
    company_name: str,
    date_from: str | None = None,
    date_to: str | None = None,
    act_type: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Busca actos registrales en el BORME (Boletín Oficial del Registro Mercantil).

    Permite localizar inscripciones de constitución, nombramientos, ceses,
    ampliaciones de capital y otros actos mercantiles de una empresa.

    Cubre desde el 02-01-2009, que es cuando la edición electrónica pasó a ser la
    oficial. Devuelve las más recientes primero.

    Si la respuesta trae `meta.has_more` a true hay más de las que caben: acota con
    `date_from`/`date_to` o con `act_type` en vez de pedir una página mayor. Un grupo
    como Telefónica tiene miles, y de un año concreto tiene unas trescientas.

    Args:
        company_name: Nombre o razón social de la empresa a buscar.
        date_from: Fecha de inicio de búsqueda (formato YYYY-MM-DD, opcional).
        date_to: Fecha de fin de búsqueda (formato YYYY-MM-DD, opcional).
        act_type: Tipo de acto, tal como lo escribe el boletín (opcional):
            Nombramientos, Ceses/Dimisiones, Constitución, Revocaciones,
            Reelecciones, Ampliación de capital, Reducción de capital,
            Modificaciones estatutarias, Cambio de domicilio social,
            Cambio de objeto social, Cambio de denominación social,
            Declaración de unipersonalidad, Disolución, Extinción,
            Situación concursal, Fusión por absorción, Otros conceptos.
            Se compara sin distinguir mayúsculas ni tildes; si el tipo no
            existe, la respuesta trae la lista de los válidos.
        limit: Cuántas devolver. Por defecto 25, como mucho 100. Acotar por
            fecha o por tipo de acto sigue siendo mejor que pedir más: un año
            de un grupo grande son cientos de anuncios.
    """
    client = DatapremApiClient()
    return client.search_borme(
        company_name=company_name,
        date_from=date_from,
        date_to=date_to,
        act_type=act_type,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Tool: Subvenciones — REAL (DataPrem API, no stub)
# ---------------------------------------------------------------------------


@mcp.tool(description=DESCRIPTIONS["dataprem_subsidies_search"])
def dataprem_subsidies_search(
    query: str | None = None,
    beneficiary: str | None = None,
    body: str | None = None,
    level: str | None = None,
    min_amount: str | None = None,
    max_amount: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Busca subvenciones y ayudas públicas españolas concedidas, y quién las recibió.

    Consulta la Base de Datos Nacional de Subvenciones: concesiones con su
    importe, la convocatoria de la que salen y el órgano que las concede. Al
    menos un filtro es obligatorio: buscarlo todo no es una búsqueda.

    Buscar sin acentos y en minúsculas encuentra igual. `meta.has_more` dice si
    hay más de las que caben, y `meta.years` en qué años, para acotar sin
    adivinar. Al citar estos datos hay que indicar el origen, que viaja en
    `meta.source`.

    Args:
        query: Palabras del título de la convocatoria (ej. "ayudas a la contratación").
        beneficiary: Quién recibió el dinero, por nombre o NIF. Las personas
            físicas llegan seudonimizadas en origen, así que sólo empresas y
            entidades llevan NIF.
        body: Órgano que la concedió, o parte de su nombre. También encuentra
            por comunidad autónoma ("navarra").
        level: ESTADO, AUTONOMICA o LOCAL, separados por comas.
        min_amount: Importe mínimo concedido, en euros.
        max_amount: Importe máximo concedido, en euros.
        date_from: Fecha mínima de concesión (formato YYYY-MM-DD).
        date_to: Fecha máxima de concesión (formato YYYY-MM-DD).
        limit: Cuántas devolver. Por defecto 25, como mucho 100.
    """
    client = DatapremApiClient()
    return client.search_subsidies(
        query=query,
        beneficiary=beneficiary,
        body=body,
        level=level,
        min_amount=min_amount,
        max_amount=max_amount,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Tool: Licitaciones públicas — planned, answered by the API
# ---------------------------------------------------------------------------


@mcp.tool(description=DESCRIPTIONS["dataprem_tenders_search"])
def dataprem_tenders_search(
    query: str | None = None,
    location: str | None = None,
    status: str | None = None,
    buyer: str | None = None,
    company: str | None = None,
    cpv: str | None = None,
    min_amount: str | None = None,
    max_amount: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Busca licitaciones y contratos públicos en España.

    Consulta la Plataforma de Contratación del Sector Público: licitaciones
    publicadas, en evaluación, adjudicadas o resueltas, con quién las ganó y
    por cuánto. Al menos un filtro es obligatorio: buscarlo todo no es una
    búsqueda.

    Buscar sin acentos y en minúsculas encuentra igual. `meta.has_more` dice si
    hay más resultados sin contarlos, y `meta.years` en qué años los hay, para
    acotar sin adivinar.

    Args:
        query: Términos sobre el objeto del contrato. Casan palabra a palabra, sin acentos y en minúsculas.
        location: Provincia, ciudad o código NUTS (ES300).
        status: "open", "closed", "all", o los códigos PRE, PUB, EV, ADJ, RES, ANUL separados por comas.
        buyer: Organismo público que saca el concurso, o parte de su nombre.
        company: Empresa adjudicataria, por nombre o por NIF. Responde "qué se ha llevado esta empresa".
        cpv: Código CPV o su prefijo, de 2 a 10 dígitos, separados por comas. 45 es toda la construcción.
        min_amount: Presupuesto mínimo sin impuestos, en euros.
        max_amount: Presupuesto máximo sin impuestos, en euros.
        date_from: Fecha de publicación más antigua (Y-m-d).
        date_to: Fecha de publicación más reciente (Y-m-d).
        limit: Cuántas devolver. Por defecto 25, tope 100.
    """
    client = DatapremApiClient()
    return client.search_tenders(
        query=query,
        location=location,
        status=status,
        buyer=buyer,
        company=company,
        cpv=cpv,
        min_amount=min_amount,
        max_amount=max_amount,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
