"""DataPrem MCP Server.

Exposes Spanish public data sources (Catastro, BORME, CENDOJ, Licitaciones)
as MCP tools for AI agents. Catastro is wired against the real DataPrem REST
API (`api.dataprem.com`); the rest are stubs scheduled by phase — see README
for the live status table.
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
    "dataprem_cendoj_search",
    "dataprem_tenders_search",
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
# Tool: CENDOJ — planned, answered by the API
# ---------------------------------------------------------------------------


@mcp.tool(description=DESCRIPTIONS["dataprem_cendoj_search"])
def dataprem_cendoj_search(
    query: str,
    court: str | None = None,
    date_from: str | None = None,
) -> dict[str, Any]:
    """Busca resoluciones judiciales en el CENDOJ (Centro de Documentación Judicial).

    Permite buscar sentencias, autos y providencias de todos los órdenes
    jurisdiccionales españoles.

    Args:
        query: Términos de búsqueda (texto libre sobre la materia de la resolución).
        court: Órgano judicial (ej. "Tribunal Supremo", "Audiencia Provincial de Madrid"). Opcional.
        date_from: Fecha mínima de la resolución (formato YYYY-MM-DD, opcional).
    """
    client = DatapremApiClient()
    return client.search_cendoj(query=query, court=court, date_from=date_from)


# ---------------------------------------------------------------------------
# Tool: Licitaciones públicas — planned, answered by the API
# ---------------------------------------------------------------------------


@mcp.tool(description=DESCRIPTIONS["dataprem_tenders_search"])
def dataprem_tenders_search(
    query: str,
    location: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Busca licitaciones y contratos públicos en España.

    Consulta la Plataforma de Contratación del Sector Público para encontrar
    licitaciones abiertas, adjudicadas o cerradas.

    Args:
        query: Términos de búsqueda sobre el objeto del contrato.
        location: Comunidad autónoma o provincia (opcional).
        status: Estado de la licitación: "open" (abierta), "closed" (cerrada) o "all" (todas). Por defecto "all".
    """
    client = DatapremApiClient()
    return client.search_tenders(query=query, location=location, status=status)
