/**
 * Static Nairobi Securities Exchange security directory.
 * Prices are never stored here: ticker is passed to the market-price endpoint on demand.
 * Source snapshot: NSE daily-price-list-derived market board, September 2026.
 */
export const NSE_SECURITIES = [
  ["SCOM","Safaricom Plc","TELECOMMUNICATION"],
  ["KPLC","Kenya Power & Lighting Co Plc","ENERGY & PETROLEUM"],
  ["HFCK","HF Group Plc","BANKING"],
  ["KEGN","KenGen Co. Plc","ENERGY & PETROLEUM"],
  ["CIC","CIC Insurance Group Ltd","INSURANCE"],
  ["EQTY","Equity Group Holdings Plc","BANKING"],
  ["KQ","Kenya Airways Ltd","COMMERCIAL AND SERVICES"],
  ["KNRE","Kenya Re Insurance Corporation Ltd","INSURANCE"],
  ["ABSA","ABSA Bank Kenya Plc","BANKING"],
  ["COOP","The Co-operative Bank of Kenya Ltd","BANKING"],
  ["NSE","Nairobi Securities Exchange Plc","INVESTMENT SERVICES"],
  ["DTK","Diamond Trust Bank Kenya Ltd","BANKING"],
  ["HAFR","Home Afrika Ltd","INVESTMENT"],
  ["IMH","I&M Holdings Plc","BANKING"],
  ["FMLY","Family Bank Limited","BANKING"],
  ["SBIC","Stanbic Holdings Plc","BANKING"],
  ["EVRD","Eveready East Africa Ltd","COMMERCIAL AND SERVICES"],
  ["UCHM","Uchumi Supermarket Plc","COMMERCIAL AND SERVICES"],
  ["CTUM","Centum Investment Co Plc","INVESTMENT"],
  ["BRIT","Britam Holdings Plc","INSURANCE"],
  ["EABL","East African Breweries Ltd","MANUFACTURING & ALLIED"],
  ["NBV","Nairobi Business Ventures Ltd","COMMERCIAL AND SERVICES"],
  ["SCAN","WPP Scangroup Plc","COMMERCIAL AND SERVICES"],
  ["UMME","Umeme Ltd","ENERGY & PETROLEUM"],
  ["CARB","Carbacid Investments Ltd","MANUFACTURING & ALLIED"],
  ["SLAM","Sanlam Kenya Plc","INSURANCE"],
  ["FTGH","Flame Tree Group Holdings Ltd","MANUFACTURING & ALLIED"],
  ["NMG","Nation Media Group Plc","COMMERCIAL AND SERVICES"],
  ["SKL","Shri Krishana Overseas Plc","MANUFACTURING & ALLIED"],
  ["SMER","Sameer Africa Plc","COMMERCIAL AND SERVICES"],
  ["TOTL","Total Kenya Ltd","ENERGY & PETROLEUM"],
  ["SCBK","Standard Chartered Bank Kenya Ltd","BANKING"],
  ["XPRS","Express Kenya Plc","COMMERCIAL AND SERVICES"],
  ["BKG","BK Group Plc","BANKING"],
  ["LKL","Longhorn Publishers Plc","COMMERCIAL AND SERVICES"],
  ["CGEN","Car & General (K) Ltd","AUTOMOBILES & ACCESSORIES"],
  ["BAT","British American Tobacco Kenya Plc","MANUFACTURING & ALLIED"],
  ["UNGA","Unga Group Ltd","MANUFACTURING & ALLIED"],
  ["WTK","Williamson Tea Kenya Ltd","AGRICULTURAL"],
  ["SASN","Sasini Plc","AGRICULTURAL"],
  ["LBTY","Liberty Kenya Holdings Ltd","INSURANCE"],
  ["TPSE","TPS Eastern Africa Ltd","COMMERCIAL AND SERVICES"],
  ["SGL","Standard Group Plc","COMMERCIAL AND SERVICES"],
  ["KCB","KCB Group Plc","BANKING"],
  ["CRWN","Crown Paints Kenya Plc","CONSTRUCTION & ALLIED"],
  ["PORT","E.A. Portland Cement Co. Ltd","CONSTRUCTION & ALLIED"],
  ["KAPC","Kapchorua Tea Co. Ltd","AGRICULTURAL"],
  ["JUB","Jubilee Holdings Ltd","INSURANCE"],
  ["KPC","Kenya Pipeline Company Plc","ENERGY & PETROLEUM"],
  ["AMAC","Africa Mega Agricorp Plc","MANUFACTURING & ALLIED"],
  ["KPLC.P0004","Kenya Power & Lighting Plc 4% Preference","ENERGY & PETROLEUM"],
  ["EGAD","Eaagads Ltd","AGRICULTURAL"],
  ["OCH","Olympia Capital Holdings Ltd","INVESTMENT"],
  ["KUKZ","Kakuzi Plc","AGRICULTURAL"],
  ["LIMT","The Limuru Tea Co. Plc","AGRICULTURAL"],
  ["NCBA","NCBA Group Plc","BANKING"],
  ["KURV","Kurwitu Ventures Ltd","INVESTMENT"],
  ["BOC","B.O.C Kenya Plc","MANUFACTURING & ALLIED"],
  ["BAMB","Bamburi Cement Ltd","CONSTRUCTION & ALLIED"],
  ["CABL","E.A. Cables Ltd","CONSTRUCTION & ALLIED"],
  ["DCON","Deacons (East Africa) Plc","COMMERCIAL AND SERVICES"],
  ["HBE","Homeboyz Entertainment Plc","COMMERCIAL AND SERVICES"],
  ["MSC","Mumias Sugar Co. Ltd","MANUFACTURING & ALLIED"],
  ["TCL","Trans-Century Plc","INVESTMENT"],
  ["ARM","ARM Cement Plc","CONSTRUCTION & ALLIED"]
].map(([ticker,name,sector]) => ({ticker,name,sector}));

export const NSE_STOCKS_BY_TICKER = Object.freeze(
  Object.fromEntries(NSE_SECURITIES.map(stock => [stock.ticker, stock]))
);

export function nseCompanyName(ticker) {
  return NSE_STOCKS_BY_TICKER[String(ticker || "").trim().toUpperCase()]?.name || "";
}
