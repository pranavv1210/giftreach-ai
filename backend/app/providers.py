import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse, urljoin
import httpx
from .config import get_settings

ROLE_WORDS=("hr","human resources","people","employee engagement","administration","admin","procurement","workplace","talent","culture")
EMAIL_RE=re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",re.I)
class ProviderUnavailable(RuntimeError): pass

@dataclass
class CompanyFinding:
    name:str; domain:str; website:str; source_url:str; evidence:str; query:str
@dataclass
class ContactFinding:
    email:str; source_url:str; description:str; confidence:float; source_type:str="PUBLICLY_LISTED"

class BraveDiscoveryProvider:
    name="brave"
    def __init__(self,client=None): self.client=client or httpx.Client(timeout=15,follow_redirects=True,headers={"User-Agent":"GiftReachResearch/1.0"})
    def search(self,query,count=10):
        key=get_settings().brave_search_api_key or get_settings().search_api_key
        if not key: raise ProviderUnavailable("Brave Search is not configured. Set BRAVE_SEARCH_API_KEY.")
        r=self.client.get("https://api.search.brave.com/res/v1/web/search",params={"q":query,"count":min(count,20),"country":"IN","search_lang":"en"},headers={"X-Subscription-Token":key,"Accept":"application/json"})
        r.raise_for_status();return r.json().get("web",{}).get("results",[])
    def discover_companies(self,queries,limit):
        seen=set();findings=[];blocked=("linkedin.com","facebook.com","instagram.com","youtube.com","wikipedia.org","justdial.com")
        for query in queries:
            for result in self.search(query,min(limit,20)):
                url=result.get("url","");host=urlparse(url).netloc.lower().removeprefix("www.")
                if not host or any(x in host for x in blocked) or host in seen:continue
                seen.add(host);title=re.split(r"[|–—-]",unescape(result.get("title",host)))[0].strip()
                findings.append(CompanyFinding(title or host,host,f"https://{host}",url,result.get("description","")[:1000],query))
                if len(findings)>=limit:return findings
        return findings

class OfficialWebsiteContactProvider:
    name="official_website"
    def __init__(self,client=None): self.client=client or httpx.Client(timeout=12,follow_redirects=True,headers={"User-Agent":"GiftReachResearch/1.0"})
    def discover(self,website,limit=3):
        pages=[website,urljoin(website,"/contact"),urljoin(website,"/about"),urljoin(website,"/team"),urljoin(website,"/careers")]
        host=urlparse(website).netloc.lower().removeprefix("www.");found={}
        for url in pages:
            try:
                r=self.client.get(url)
                if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""):continue
                text=unescape(r.text[:2_000_000]);lower=text.lower()
                for email in EMAIL_RE.findall(text):
                    email=email.lower().strip(".,;:>")
                    if email.split("@")[-1].removeprefix("www.")!=host:continue
                    pos=lower.find(email);context=lower[max(0,pos-120):pos+len(email)+120];local=email.split("@")[0]
                    if any(w in context or w in local for w in ROLE_WORDS) and email not in found:found[email]=ContactFinding(email,url,"Publicly listed on the official company website",.65)
                    if len(found)>=limit:return list(found.values())
            except (httpx.HTTPError,ValueError):continue
        return list(found.values())

def campaign_queries(campaign):
    locations=campaign.cities or campaign.districts or ["Bengaluru"];industries=campaign.industries or ["company","business"]
    return [f'{industry} companies in {location} Karnataka official website' for location in locations for industry in industries[:5]][:10]
