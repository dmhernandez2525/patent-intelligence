"""EPO Open Patent Services ingester.

Fetches patent data from EPO DOCDB and INPADOC databases,
covering 90+ countries with bibliographic, legal status, and family data.
"""
from collections.abc import AsyncGenerator
from datetime import datetime

from src.ingesters.base import BaseIngester, RawPatentData
from src.ingesters.epo_client import EPOAPIError, EPOAuthError, EPOClient
from src.pipeline.normalizer import normalize_cpc_code, normalize_patent_number
from src.utils.logger import logger


class EPOIngester(BaseIngester):
    """Ingester for EPO Open Patent Services data."""

    source_name = "epo"

    def __init__(self, consumer_key: str | None = None, consumer_secret: str | None = None):
        self.client = EPOClient(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
        )

    async def close(self) -> None:
        await self.client.close()

    async def fetch_patents(
        self,
        offset: int = 0,
        limit: int = 25,
        since: datetime | None = None,
    ) -> AsyncGenerator[list[RawPatentData], None]:
        """
        Fetch patents from EPO using search API.

        Uses CQL (Common Query Language) to search recent publications.
        EPO limits to 100 results per request and 2000 total per query.
        """
        query = self._build_search_query(since)
        batch_size = min(limit, 25)  # EPO max per request is 100, but 25 is safer
        range_begin = offset + 1
        total_fetched = 0

        while total_fetched < limit:
            range_end = min(range_begin + batch_size - 1, range_begin + limit - total_fetched - 1)

            try:
                result = await self.client.search_publications(
                    query=query,
                    range_begin=range_begin,
                    range_end=range_end,
                )
            except EPOAPIError as e:
                if e.status_code == 404:
                    break
                logger.error("epo.search_error", error=str(e))
                break
            except EPOAuthError as e:
                logger.error("epo.auth_error", error=str(e))
                break

            if not result:
                break

            patents = self._parse_search_results(result)
            if not patents:
                break

            yield patents
            total_fetched += len(patents)
            range_begin += len(patents)

            # Check if we've reached the end of results
            total_count = self._get_total_count(result)
            if total_count and range_begin > total_count:
                break

    async def fetch_patent_detail(self, patent_number: str) -> RawPatentData | None:
        """Fetch detailed data for a single patent from EPO DOCDB."""
        try:
            result = await self.client.get_published_data(
                reference_type="publication",
                input_format="epodoc",
                number=patent_number,
                endpoint="full-cycle",
            )
        except (EPOAPIError, EPOAuthError) as e:
            logger.error("epo.detail_error", patent=patent_number, error=str(e))
            return None

        if not result:
            return None

        return self._parse_full_patent(result, patent_number)

    async def fetch_legal_status(self, patent_number: str) -> list[dict]:
        """Fetch legal status events for a patent."""
        try:
            result = await self.client.get_legal_status(
                reference_type="publication",
                input_format="epodoc",
                number=patent_number,
            )
        except (EPOAPIError, EPOAuthError) as e:
            logger.error("epo.legal_error", patent=patent_number, error=str(e))
            return []

        if not result:
            return []

        return self._parse_legal_events(result)

    async def fetch_family_members(self, patent_number: str) -> list[dict]:
        """Fetch patent family members from INPADOC."""
        try:
            result = await self.client.get_family(
                reference_type="publication",
                input_format="epodoc",
                number=patent_number,
            )
        except (EPOAPIError, EPOAuthError) as e:
            logger.error("epo.family_error", patent=patent_number, error=str(e))
            return []

        if not result:
            return []

        return self._parse_family_members(result)

    def _build_search_query(self, since: datetime | None = None) -> str:
        """Build CQL search query for EPO OPS."""
        # Search for granted patents in major jurisdictions
        query_parts = ["pd>=2020"]  # Published date from 2020 onwards

        if since:
            date_str = since.strftime("%Y%m%d")
            query_parts = [f"pd>={date_str}"]

        # Focus on key patent offices
        query_parts.append("(pn=EP OR pn=WO OR pn=GB OR pn=DE OR pn=FR)")

        return " AND ".join(query_parts)

    def _get_total_count(self, result: dict) -> int | None:
        """Extract total result count from search response."""
        try:
            biblio_search = result.get("ops:world-patent-data", {}).get(
                "ops:biblio-search", {}
            )
            total = biblio_search.get("@total-result-count")
            return int(total) if total else None
        except (ValueError, TypeError):
            return None

    def _parse_search_results(self, result: dict) -> list[RawPatentData]:
        """Parse EPO search response into RawPatentData list."""
        patents = []

        try:
            biblio_search = result.get("ops:world-patent-data", {}).get(
                "ops:biblio-search", {}
            )
            search_result = biblio_search.get("ops:search-result", {})
            exchange_docs = search_result.get("exchange-documents", [])

            # Ensure it's a list
            if isinstance(exchange_docs, dict):
                exchange_docs = [exchange_docs]

            for doc_wrapper in exchange_docs:
                doc = doc_wrapper.get("exchange-document", {})
                if isinstance(doc, list):
                    doc = doc[0] if doc else {}

                patent = self._parse_exchange_document(doc)
                if patent:
                    patents.append(patent)

        except Exception as e:
            logger.error("epo.parse_error", error=str(e))

        return patents

    def _parse_exchange_document(self, doc: dict) -> RawPatentData | None:
        """Parse a single exchange-document into RawPatentData."""
        try:
            # Extract document ID
            country = doc.get("@country", "")
            doc_number = doc.get("@doc-number", "")
            kind = doc.get("@kind", "")

            if not doc_number:
                return None

            patent_number = f"{country}{doc_number}"
            if kind:
                patent_number = f"{patent_number}{kind}"

            # Extract bibliographic data
            biblio = doc.get("bibliographic-data", {})

            title = self._extract_title(biblio)
            if not title:
                title = f"Patent {patent_number}"

            abstract = self._extract_abstract(doc)
            filing_date = self._extract_date(biblio, "application-reference")
            publication_date = self._extract_date(biblio, "publication-reference")
            priority_date = self._extract_priority_date(biblio)

            # Parties
            assignee, assignee_org = self._extract_applicants(biblio)
            inventors = self._extract_inventors(biblio)

            # Classifications
            cpc_codes = self._extract_classifications(biblio, "patent-classification", "CPC")
            ipc_codes = self._extract_classifications(biblio, "classification-ipc", "IPC")

            return RawPatentData(
                patent_number=normalize_patent_number(patent_number, country or "EP"),
                title=title,
                abstract=abstract,
                filing_date=filing_date,
                publication_date=publication_date,
                priority_date=priority_date,
                assignee=assignee,
                assignee_organization=assignee_org,
                inventors=inventors,
                cpc_codes=cpc_codes,
                ipc_codes=ipc_codes,
                patent_type="utility",
                country=country or "EP",
                kind_code=kind,
                status="active",
                raw_data=doc,
            )

        except Exception as e:
            logger.warning("epo.parse_doc_error", error=str(e))
            return None

    def _parse_full_patent(self, result: dict, patent_number: str) -> RawPatentData | None:
        """Parse full-cycle response into RawPatentData."""
        try:
            world_data = result.get("ops:world-patent-data", {})
            exchange_docs = world_data.get("exchange-documents", {}).get(
                "exchange-document", {}
            )

            if isinstance(exchange_docs, list):
                exchange_docs = exchange_docs[0] if exchange_docs else {}

            patent = self._parse_exchange_document(exchange_docs)
            if patent:
                # Extract claims if available
                claims_data = exchange_docs.get("claims", {})
                if claims_data:
                    patent.claims = self._parse_claims(claims_data)

                # Extract description if available
                desc_data = exchange_docs.get("description", {})
                if desc_data:
                    patent.description = self._extract_text_content(desc_data)

            return patent

        except Exception as e:
            logger.error("epo.parse_full_error", patent=patent_number, error=str(e))
            return None

    def _extract_title(self, biblio: dict) -> str | None:
        """Extract English title from bibliographic data."""
        invention_title = biblio.get("invention-title", [])
        if isinstance(invention_title, dict):
            invention_title = [invention_title]

        for title_entry in invention_title:
            if isinstance(title_entry, dict):
                lang = title_entry.get("@lang", "")
                if lang == "en":
                    return title_entry.get("$", "")

        # Fallback to first available title
        if invention_title:
            entry = invention_title[0]
            if isinstance(entry, dict):
                return entry.get("$", "")
            return str(entry) if entry else None

        return None

    def _extract_abstract(self, doc: dict) -> str | None:
        """Extract English abstract."""
        abstracts = doc.get("abstract", [])
        if isinstance(abstracts, dict):
            abstracts = [abstracts]

        for abstract_entry in abstracts:
            if isinstance(abstract_entry, dict):
                lang = abstract_entry.get("@lang", "")
                if lang == "en":
                    paragraphs = abstract_entry.get("p", [])
                    return self._extract_text_content({"p": paragraphs})

        # Fallback to first abstract
        if abstracts:
            entry = abstracts[0]
            if isinstance(entry, dict):
                paragraphs = entry.get("p", [])
                return self._extract_text_content({"p": paragraphs})

        return None

    def _extract_date(self, biblio: dict, ref_type: str) -> str | None:
        """Extract date from a reference section."""
        ref = biblio.get(ref_type, {})
        if isinstance(ref, list):
            ref = ref[0] if ref else {}

        doc_id = ref.get("document-id", [])
        if isinstance(doc_id, list):
            for did in doc_id:
                date_val = did.get("date", {}).get("$", "")
                result = self._parse_epo_date(date_val)
                if result:
                    return result
        elif isinstance(doc_id, dict):
            date_val = doc_id.get("date", {}).get("$", "")
            return self._parse_epo_date(date_val)

        return None

    @staticmethod
    def _parse_epo_date(date_val: str) -> str | None:
        """Parse and validate a date string in YYYYMMDD format."""
        if not date_val or len(date_val) < 8:
            return None
        try:
            from datetime import datetime
            parsed = datetime.strptime(date_val[:8], "%Y%m%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _extract_priority_date(self, biblio: dict) -> str | None:
        """Extract earliest priority date."""
        priority = biblio.get("priority-claims", {}).get("priority-claim", [])
        if isinstance(priority, dict):
            priority = [priority]

        dates = []
        for claim in priority:
            doc_id = claim.get("document-id", {})
            if isinstance(doc_id, list):
                doc_id = doc_id[0] if doc_id else {}
            date_val = doc_id.get("date", {}).get("$", "")
            if date_val and len(date_val) >= 8:
                dates.append(f"{date_val[:4]}-{date_val[4:6]}-{date_val[6:8]}")

        return min(dates) if dates else None

    def _extract_applicants(self, biblio: dict) -> tuple[str | None, str | None]:
        """Extract applicant/assignee information."""
        parties = biblio.get("parties", {})
        applicants = parties.get("applicants", {}).get("applicant", [])
        if isinstance(applicants, dict):
            applicants = [applicants]

        for applicant in applicants:
            if applicant.get("@data-format") == "epodoc":
                name = applicant.get("applicant-name", {}).get("name", {}).get("$", "")
                if name:
                    return name, name

        return None, None

    def _extract_inventors(self, biblio: dict) -> list[str] | None:
        """Extract inventor names."""
        parties = biblio.get("parties", {})
        inventors_data = parties.get("inventors", {}).get("inventor", [])
        if isinstance(inventors_data, dict):
            inventors_data = [inventors_data]

        names = []
        for inventor in inventors_data:
            if inventor.get("@data-format") == "epodoc":
                name = inventor.get("inventor-name", {}).get("name", {}).get("$", "")
                if name:
                    names.append(name)

        return names if names else None

    def _extract_classifications(
        self,
        biblio: dict,
        section: str,
        scheme: str,
    ) -> list[str] | None:
        """Extract patent classifications (CPC or IPC)."""
        classifications = biblio.get("patent-classifications", {}).get(
            "patent-classification", []
        )
        if isinstance(classifications, dict):
            classifications = [classifications]

        codes = []
        for cls in classifications:
            cls_scheme = cls.get("classification-scheme", {}).get("@scheme", "")
            if cls_scheme.upper() == scheme.upper() or not scheme:
                section_val = cls.get("section", {}).get("$", "")
                class_val = cls.get("class", {}).get("$", "")
                subclass_val = cls.get("subclass", {}).get("$", "")
                main_group = cls.get("main-group", {}).get("$", "")
                subgroup = cls.get("subgroup", {}).get("$", "")

                if section_val and class_val:
                    code = f"{section_val}{class_val}{subclass_val}"
                    if main_group:
                        code = f"{code}{main_group}"
                        if subgroup:
                            code = f"{code}/{subgroup}"
                    codes.append(normalize_cpc_code(code))

        return codes if codes else None

    def _parse_claims(self, claims_data: dict) -> list[dict] | None:
        """Parse claims section into structured data."""
        claims = []
        claim_list = claims_data.get("claim", [])
        if isinstance(claim_list, dict):
            claim_list = [claim_list]

        for i, claim in enumerate(claim_list):
            claim_text = self._extract_text_content(claim)
            if claim_text:
                claims.append({
                    "claim_number": i + 1,
                    "text": claim_text,
                    "type": "independent" if i == 0 else "dependent",
                })

        return claims if claims else None

    def _parse_legal_events(self, result: dict) -> list[dict]:
        """Parse legal status response into event list."""
        events = []
        try:
            world_data = result.get("ops:world-patent-data", {})
            legal_data = world_data.get("ops:register-search", {}).get(
                "reg:register-documents", {}
            ).get("reg:register-document", [])

            if isinstance(legal_data, dict):
                legal_data = [legal_data]

            for doc in legal_data:
                legal_events = doc.get("reg:bibliographic-data", {}).get(
                    "reg:events", {}
                ).get("reg:event", [])

                if isinstance(legal_events, dict):
                    legal_events = [legal_events]

                for event in legal_events:
                    event_data = event.get("reg:event-data", {})
                    events.append({
                        "event_code": event_data.get("reg:event-code", {}).get("$", ""),
                        "event_date": event_data.get("reg:event-date", {}).get("$", ""),
                        "event_text": event_data.get("reg:event-text", {}).get("$", ""),
                    })

        except Exception as e:
            logger.warning("epo.parse_legal_error", error=str(e))

        return events

    def _parse_family_members(self, result: dict) -> list[dict]:
        """Parse family response into member list."""
        members = []
        try:
            world_data = result.get("ops:world-patent-data", {})
            family_data = world_data.get("ops:patent-family", {}).get(
                "ops:family-member", []
            )

            if isinstance(family_data, dict):
                family_data = [family_data]

            for member in family_data:
                pub_ref = member.get("publication-reference", {})
                doc_id = pub_ref.get("document-id", [])
                if isinstance(doc_id, list):
                    doc_id = doc_id[0] if doc_id else {}

                country = doc_id.get("country", {}).get("$", "")
                doc_number = doc_id.get("doc-number", {}).get("$", "")
                kind = doc_id.get("kind", {}).get("$", "")

                if doc_number:
                    members.append({
                        "patent_number": f"{country}{doc_number}{kind}",
                        "country": country,
                        "kind_code": kind,
                    })

        except Exception as e:
            logger.warning("epo.parse_family_error", error=str(e))

        return members

    @staticmethod
    def _extract_text_content(data: dict) -> str | None:
        """Extract text content from nested paragraph/text structures."""
        paragraphs = data.get("p", [])
        if isinstance(paragraphs, str):
            return paragraphs
        if isinstance(paragraphs, dict):
            return paragraphs.get("$", "")
        if isinstance(paragraphs, list):
            texts = []
            for p in paragraphs:
                if isinstance(p, str):
                    texts.append(p)
                elif isinstance(p, dict):
                    texts.append(p.get("$", ""))
            return " ".join(texts) if texts else None
        return None
