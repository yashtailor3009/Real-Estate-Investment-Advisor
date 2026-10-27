-- =====================================================================
--  REAL ESTATE INVESTMENT ADVISOR  -  SQL INSIGHTS
--  Dialect : SQLite (also runs in the Streamlit SQL playground)
--  Table   : properties   (250,000 rows, produced by scripts/run_pipeline.py)
--
--  Key columns
--    Price_in_Lakhs ........ price in INR lakhs (1 lakh = 100,000)
--    Price_per_SqFt_INR .... price per sq ft in rupees
--    Value_Ratio ........... price/sqft vs city median (1.0 = at median)
--    Infra_Score ........... 0-100 neighbourhood score (schools+hospitals+transit)
--    Annual_Appreciation ... projected yearly price growth (domain-rule model)
--    Future_Price_5Y_Lakhs . projected price after 5 years
--    Good_Investment ....... 1 if appreciation >= 9 % AND Value_Ratio <= 1.5
--
--  NOTE: Annual_Appreciation / Future_Price / Good_Investment are MODELLED
--  from transparent domain rules (see src/data_processing.py) - the raw file
--  has no time series. Insights tagged MODELLED reflect those rules.
--
--  Each query starts with an  @id / @section / @title / @insight  header
--  which the app uses to build its query library.
-- =====================================================================


-- =====================================================================
-- SECTION A : DATA QUALITY
-- =====================================================================

-- @id: Q01
-- @section: Data Quality
-- @title: Dataset health check (rows, duplicates, missing values)
-- @insight: Confirms the file is complete and unique before any analysis.
SELECT COUNT(*)                                        AS total_rows,
       COUNT(DISTINCT ID)                              AS unique_ids,
       SUM(CASE WHEN Price_in_Lakhs   IS NULL THEN 1 ELSE 0 END) AS null_price,
       SUM(CASE WHEN Size_in_SqFt     IS NULL THEN 1 ELSE 0 END) AS null_size,
       SUM(CASE WHEN City             IS NULL THEN 1 ELSE 0 END) AS null_city,
       COUNT(DISTINCT State)                           AS states,
       COUNT(DISTINCT City)                            AS cities,
       COUNT(DISTINCT Locality)                        AS localities
FROM properties;

-- @id: Q02
-- @section: Data Quality
-- @title: Impossible floors (Floor_No above Total_Floors)
-- @insight: Nearly half the rows list a floor higher than the building - a source-data issue to fix at capture.
SELECT SUM(Floor_Inconsistent)                          AS inconsistent_rows,
       ROUND(100.0 * AVG(Floor_Inconsistent), 1)        AS pct_of_rows
FROM properties;

-- @id: Q03
-- @section: Data Quality
-- @title: Outlier counts (IQR rule) for price/sqft and size
-- @insight: Price per sq ft has a long right tail; size is uniformly spread so it has no outliers.
SELECT 'Price_per_SqFt' AS metric, SUM(PPSF_Outlier) AS outliers,
       ROUND(100.0 * AVG(PPSF_Outlier), 2) AS pct
FROM properties
UNION ALL
SELECT 'Size_in_SqFt', SUM(Size_Outlier), ROUND(100.0 * AVG(Size_Outlier), 2)
FROM properties;


-- =====================================================================
-- SECTION B : PRICE AND SIZE ANALYSIS  (EDA questions 1-5)
-- =====================================================================

-- @id: Q04
-- @section: Price & Size
-- @title: Distribution of property prices (100-lakh bands)
-- @insight: Prices are spread almost evenly from 10 to 500 lakhs - there is no 'typical' price tier.
SELECT Price_Band,
       COUNT(*)                                   AS properties,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_share
FROM properties
GROUP BY Price_Band
ORDER BY MIN(Price_in_Lakhs);

-- @id: Q05
-- @section: Price & Size
-- @title: Distribution of property sizes (500 sq ft bands)
-- @insight: Every size band from 500 to 5,000 sq ft holds roughly the same share of listings.
SELECT (CAST((Size_in_SqFt - 1) / 500 AS INT) * 500 + 1) || '-' ||
       (CAST((Size_in_SqFt - 1) / 500 AS INT) * 500 + 500) AS size_band_sqft,
       COUNT(*)                                   AS properties,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_share
FROM properties
GROUP BY CAST((Size_in_SqFt - 1) / 500 AS INT)
ORDER BY CAST((Size_in_SqFt - 1) / 500 AS INT);

-- @id: Q06
-- @section: Price & Size
-- @title: Price per sq ft by property type
-- @insight: Property type barely moves price per sq ft - buyers should not pay a premium just for 'Villa'.
SELECT Property_Type,
       COUNT(*)                                   AS properties,
       ROUND(AVG(Price_per_SqFt_INR))             AS avg_ppsf_inr,
       ROUND(MIN(Price_per_SqFt_INR))             AS min_ppsf_inr,
       ROUND(MAX(Price_per_SqFt_INR))             AS max_ppsf_inr
FROM properties
GROUP BY Property_Type
ORDER BY avg_ppsf_inr DESC;

-- @id: Q07
-- @section: Price & Size
-- @title: Relationship between size and price (correlations)
-- @insight: Size has ~0 correlation with total price but a strong NEGATIVE one with price per sq ft (bigger = cheaper per sq ft).
WITH s AS (
  SELECT AVG(Size_in_SqFt) mx, AVG(Price_in_Lakhs) my, AVG(Price_per_SqFt_INR) mp,
         AVG(Size_in_SqFt * Size_in_SqFt) mxx, AVG(Price_in_Lakhs * Price_in_Lakhs) myy,
         AVG(Price_per_SqFt_INR * Price_per_SqFt_INR) mpp,
         AVG(Size_in_SqFt * Price_in_Lakhs) mxy, AVG(Size_in_SqFt * Price_per_SqFt_INR) mxp
  FROM properties)
SELECT 'Size vs Total Price'        AS pair,
       ROUND((mxy - mx*my) / SQRT((mxx - mx*mx) * (myy - my*my)), 3) AS correlation FROM s
UNION ALL
SELECT 'Size vs Price per Sq Ft',
       ROUND((mxp - mx*mp) / SQRT((mxx - mx*mx) * (mpp - mp*mp)), 3) FROM s;

-- @id: Q08
-- @section: Price & Size
-- @title: Price-per-sq-ft outliers by city (IQR rule)
-- @insight: Outliers are small-footprint, high-priced units; they distort averages, so use medians for pricing decisions.
SELECT City, COUNT(*) AS properties, SUM(PPSF_Outlier) AS outliers,
       ROUND(100.0 * AVG(PPSF_Outlier), 1) AS outlier_pct,
       ROUND(MAX(Price_per_SqFt_INR)) AS max_ppsf_inr
FROM properties
GROUP BY City
ORDER BY outlier_pct DESC
LIMIT 10;


-- =====================================================================
-- SECTION C : LOCATION ANALYSIS  (EDA questions 6-10)
-- =====================================================================

-- @id: Q09
-- @section: Location
-- @title: Average price per sq ft by state
-- @insight: State averages sit within a narrow band; location alone does not explain price in this data.
SELECT State, COUNT(*) AS properties,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr,
       ROUND(AVG(Price_in_Lakhs), 1)  AS avg_price_lakhs
FROM properties
GROUP BY State
ORDER BY avg_ppsf_inr DESC;

-- @id: Q10
-- @section: Location
-- @title: Average property price by city (top 15)
-- @insight: The priciest and cheapest cities differ by only a few lakhs - city choice matters less than entry price.
SELECT City, State, COUNT(*) AS properties,
       ROUND(AVG(Price_in_Lakhs), 1) AS avg_price_lakhs,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr
FROM properties
GROUP BY City, State
ORDER BY avg_price_lakhs DESC
LIMIT 15;

-- @id: Q11
-- @section: Location
-- @title: Median age of properties by locality (15 oldest)
-- @insight: Median age is a robust stock-age signal; older localities may need renovation budgets.
WITH ranked AS (
  SELECT Locality, Age_of_Property,
         ROW_NUMBER() OVER (PARTITION BY Locality ORDER BY Age_of_Property) AS rn,
         COUNT(*)     OVER (PARTITION BY Locality)                         AS cnt
  FROM properties)
SELECT Locality, cnt AS properties, AVG(Age_of_Property) AS median_age_years
FROM ranked
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY Locality, cnt
ORDER BY median_age_years DESC, Locality
LIMIT 15;

-- @id: Q12
-- @section: Location
-- @title: BHK distribution across cities (share of 1-5 BHK, top 12 cities)
-- @insight: Every city carries a balanced 1-5 BHK mix; supply is not skewed toward any one configuration.
SELECT City,
       COUNT(*) AS properties,
       ROUND(100.0 * SUM(BHK = 1) / COUNT(*), 1) AS pct_1bhk,
       ROUND(100.0 * SUM(BHK = 2) / COUNT(*), 1) AS pct_2bhk,
       ROUND(100.0 * SUM(BHK = 3) / COUNT(*), 1) AS pct_3bhk,
       ROUND(100.0 * SUM(BHK = 4) / COUNT(*), 1) AS pct_4bhk,
       ROUND(100.0 * SUM(BHK = 5) / COUNT(*), 1) AS pct_5bhk
FROM properties
GROUP BY City
ORDER BY properties DESC
LIMIT 12;

-- @id: Q13
-- @section: Location
-- @title: Price-per-sq-ft trend by build era for the 5 most expensive localities
-- @insight: Pricing by construction era is volatile in premium localities - newer is not automatically pricier.
WITH top5 AS (
  SELECT Locality FROM properties
  GROUP BY Locality
  ORDER BY AVG(Price_per_SqFt_INR) DESC
  LIMIT 5)
SELECT p.Locality,
       (p.Year_Built / 5) * 5          AS build_era,
       COUNT(*)                        AS properties,
       ROUND(AVG(p.Price_per_SqFt_INR)) AS avg_ppsf_inr
FROM properties p
JOIN top5 t ON t.Locality = p.Locality
GROUP BY p.Locality, build_era
ORDER BY p.Locality, build_era;


-- =====================================================================
-- SECTION D : FEATURE RELATIONSHIPS  (EDA questions 11-15)
-- =====================================================================

-- @id: Q14
-- @section: Relationships
-- @title: Correlation of numeric features with price per sq ft
-- @insight: Only size is meaningfully related to price/sqft; schools, hospitals, age and floor show no relationship.
WITH s AS (
  SELECT AVG(Price_per_SqFt_INR) mp, AVG(Price_per_SqFt_INR*Price_per_SqFt_INR) mpp,
         AVG(Size_in_SqFt) a, AVG(Size_in_SqFt*Size_in_SqFt) aa, AVG(Size_in_SqFt*Price_per_SqFt_INR) ap,
         AVG(Nearby_Schools) b, AVG(Nearby_Schools*Nearby_Schools) bb, AVG(Nearby_Schools*Price_per_SqFt_INR) bp,
         AVG(Nearby_Hospitals) c, AVG(Nearby_Hospitals*Nearby_Hospitals) cc, AVG(Nearby_Hospitals*Price_per_SqFt_INR) cp,
         AVG(Age_of_Property) d, AVG(Age_of_Property*Age_of_Property) dd, AVG(Age_of_Property*Price_per_SqFt_INR) dp,
         AVG(Infra_Score) e, AVG(Infra_Score*Infra_Score) ee, AVG(Infra_Score*Price_per_SqFt_INR) ep,
         AVG(BHK) f, AVG(BHK*BHK) ff, AVG(BHK*Price_per_SqFt_INR) fp
  FROM properties)
SELECT * FROM (
SELECT 'Size_in_SqFt'     AS feature, ROUND((ap - a*mp)/SQRT((aa - a*a)*(mpp - mp*mp)), 3) AS corr_with_ppsf FROM s
UNION ALL SELECT 'Nearby_Schools',   ROUND((bp - b*mp)/SQRT((bb - b*b)*(mpp - mp*mp)), 3) FROM s
UNION ALL SELECT 'Nearby_Hospitals', ROUND((cp - c*mp)/SQRT((cc - c*c)*(mpp - mp*mp)), 3) FROM s
UNION ALL SELECT 'Age_of_Property',  ROUND((dp - d*mp)/SQRT((dd - d*d)*(mpp - mp*mp)), 3) FROM s
UNION ALL SELECT 'Infra_Score',      ROUND((ep - e*mp)/SQRT((ee - e*e)*(mpp - mp*mp)), 3) FROM s
UNION ALL SELECT 'BHK',              ROUND((fp - f*mp)/SQRT((ff - f*f)*(mpp - mp*mp)), 3) FROM s
)
ORDER BY ABS(corr_with_ppsf) DESC;

-- @id: Q15
-- @section: Relationships
-- @title: Nearby schools vs price per sq ft
-- @insight: Schools do not lift price per sq ft; the rising Good-Investment rate is MODELLED (infrastructure feeds the appreciation rule).
SELECT Nearby_Schools,
       COUNT(*) AS properties,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr,
       ROUND(100.0 * AVG(Good_Investment), 1) AS good_investment_pct
FROM properties
GROUP BY Nearby_Schools
ORDER BY Nearby_Schools;

-- @id: Q16
-- @section: Relationships
-- @title: Nearby hospitals vs price per sq ft
-- @insight: Same flat price pattern as schools; the Good-Investment uplift is modelled, not an observed market premium.
SELECT Nearby_Hospitals,
       COUNT(*) AS properties,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr,
       ROUND(100.0 * AVG(Good_Investment), 1) AS good_investment_pct
FROM properties
GROUP BY Nearby_Hospitals
ORDER BY Nearby_Hospitals;

-- @id: Q17
-- @section: Relationships
-- @title: Price by furnished status
-- @insight: Furnishing level does not change asking price, so fully furnished homes are effectively a free upgrade.
SELECT Furnished_Status,
       COUNT(*) AS properties,
       ROUND(AVG(Price_in_Lakhs), 1)  AS avg_price_lakhs,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr
FROM properties
GROUP BY Furnished_Status
ORDER BY avg_price_lakhs DESC;

-- @id: Q18
-- @section: Relationships
-- @title: Price per sq ft by facing direction
-- @insight: No 'Vastu premium' is visible: all four directions price within about 1 % of the overall average.
SELECT Facing,
       COUNT(*) AS properties,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr,
       ROUND(100.0 * AVG(Price_per_SqFt_INR) /
             (SELECT AVG(Price_per_SqFt_INR) FROM properties) - 100, 2) AS pct_vs_overall
FROM properties
GROUP BY Facing
ORDER BY avg_ppsf_inr DESC;


-- =====================================================================
-- SECTION E : INVESTMENT / AMENITIES / OWNERSHIP  (EDA questions 16-20)
-- =====================================================================

-- @id: Q19
-- @section: Investment & Amenities
-- @title: Properties by owner type
-- @insight: Listings are split evenly across Owner, Builder and Broker channels.
SELECT Owner_Type, COUNT(*) AS properties,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_share,
       ROUND(AVG(Price_in_Lakhs), 1) AS avg_price_lakhs,
       ROUND(100.0 * AVG(Good_Investment), 1) AS good_investment_pct
FROM properties
GROUP BY Owner_Type
ORDER BY properties DESC;

-- @id: Q20
-- @section: Investment & Amenities
-- @title: Properties by availability status
-- @insight: MODELLED: under-construction homes are assumed to carry extra upside, so they win far more often on projected appreciation.
SELECT Availability_Status, COUNT(*) AS properties,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_share,
       ROUND(100.0 * AVG(Annual_Appreciation), 2) AS avg_appreciation_pct,
       ROUND(100.0 * AVG(Good_Investment), 1)     AS good_investment_pct
FROM properties
GROUP BY Availability_Status;

-- @id: Q21
-- @section: Investment & Amenities
-- @title: Does parking space affect price?
-- @insight: Parking does not change asking price; the higher Good-Investment rate comes from the modelled appreciation rule.
SELECT Parking_Space, COUNT(*) AS properties,
       ROUND(AVG(Price_in_Lakhs), 1)  AS avg_price_lakhs,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr,
       ROUND(100.0 * AVG(Good_Investment), 1) AS good_investment_pct
FROM properties
GROUP BY Parking_Space;

-- @id: Q22
-- @section: Investment & Amenities
-- @title: Amenity count vs price per sq ft and investment quality
-- @insight: MODELLED: each extra amenity adds no price but steadily lifts projected appreciation and the Good-Investment rate.
SELECT Amenity_Count, COUNT(*) AS properties,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr,
       ROUND(100.0 * AVG(Annual_Appreciation), 2) AS avg_appreciation_pct,
       ROUND(100.0 * AVG(Good_Investment), 1)     AS good_investment_pct
FROM properties
GROUP BY Amenity_Count
ORDER BY Amenity_Count;

-- @id: Q23
-- @section: Investment & Amenities
-- @title: Which individual amenities matter? (price/sqft with vs without)
-- @insight: Individual amenities barely change price per sq ft (<1 %); the Good-Investment gap is the modelled amenity effect.
SELECT amenity,
       ROUND(AVG(CASE WHEN has = 1 THEN ppsf END)) AS ppsf_with,
       ROUND(AVG(CASE WHEN has = 0 THEN ppsf END)) AS ppsf_without,
       ROUND(100.0 * AVG(CASE WHEN has = 1 THEN good END), 1) AS good_pct_with,
       ROUND(100.0 * AVG(CASE WHEN has = 0 THEN good END), 1) AS good_pct_without
FROM (
  SELECT 'Gym' AS amenity, Amenities LIKE '%Gym%' AS has, Price_per_SqFt_INR AS ppsf, Good_Investment AS good FROM properties
  UNION ALL SELECT 'Pool',       Amenities LIKE '%Pool%',       Price_per_SqFt_INR, Good_Investment FROM properties
  UNION ALL SELECT 'Garden',     Amenities LIKE '%Garden%',     Price_per_SqFt_INR, Good_Investment FROM properties
  UNION ALL SELECT 'Clubhouse',  Amenities LIKE '%Clubhouse%',  Price_per_SqFt_INR, Good_Investment FROM properties
  UNION ALL SELECT 'Playground', Amenities LIKE '%Playground%', Price_per_SqFt_INR, Good_Investment FROM properties
)
GROUP BY amenity;

-- @id: Q24
-- @section: Investment & Amenities
-- @title: Public transport accessibility vs price per sq ft and investment potential
-- @insight: High transit access carries no price premium yet a clearly higher modelled Good-Investment rate.
SELECT Public_Transport_Accessibility AS transport_access,
       COUNT(*) AS properties,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr,
       ROUND(100.0 * AVG(Annual_Appreciation), 2) AS avg_appreciation_pct,
       ROUND(100.0 * AVG(Good_Investment), 1)     AS good_investment_pct
FROM properties
GROUP BY Public_Transport_Accessibility
ORDER BY avg_appreciation_pct DESC;


-- =====================================================================
-- SECTION F : ADVANCED INVESTMENT ANALYSIS  (CTEs, windows, ranking)
-- =====================================================================

-- @id: Q25
-- @section: Investment Deep-Dive
-- @title: Top 10 cities by Good-Investment rate (with rank)
-- @insight: Good-Investment rates vary only a few points by city - screen by property, not by city.
SELECT RANK() OVER (ORDER BY AVG(Good_Investment) DESC) AS rank_no,
       City, State, COUNT(*) AS properties,
       ROUND(100.0 * AVG(Good_Investment), 1)       AS good_investment_pct,
       ROUND(100.0 * AVG(Annual_Appreciation), 2)   AS avg_appreciation_pct
FROM properties
GROUP BY City, State
ORDER BY rank_no
LIMIT 10;

-- @id: Q26
-- @section: Investment Deep-Dive
-- @title: Valuation bands - under- vs over-priced vs city median
-- @insight: MODELLED: properties priced below the city median are far more likely to qualify - entry price vs city is the biggest lever.
SELECT CASE WHEN Value_Ratio < 0.5  THEN '1. Deep discount (<0.5x)'
            WHEN Value_Ratio < 1.0  THEN '2. Below median (0.5-1x)'
            WHEN Value_Ratio < 1.5  THEN '3. Above median (1-1.5x)'
            ELSE                         '4. Premium (>1.5x)' END AS valuation_band,
       COUNT(*) AS properties,
       ROUND(100.0 * AVG(Good_Investment), 1)       AS good_investment_pct,
       ROUND(100.0 * AVG(Annual_Appreciation), 2)   AS avg_appreciation_pct,
       ROUND(AVG(Projected_Gain_Lakhs), 1)          AS avg_gain_lakhs
FROM properties
GROUP BY valuation_band
ORDER BY valuation_band;

-- @id: Q27
-- @section: Investment Deep-Dive
-- @title: Top 20 'best-buy' properties (Good Investment, highest projected gain per lakh)
-- @insight: A shortlist generator: cheap-vs-city, strong infrastructure, under construction, high 5-year gain.
SELECT ID, City, Property_Type, BHK, Size_in_SqFt, Price_in_Lakhs,
       Future_Price_5Y_Lakhs, ROUND(100.0 * Annual_Appreciation, 2) AS appreciation_pct,
       ROUND(Projected_Gain_Lakhs / Price_in_Lakhs, 2) AS gain_per_lakh,
       Value_Ratio, Infra_Score
FROM properties
WHERE Good_Investment = 1 AND Price_in_Lakhs >= 50
ORDER BY gain_per_lakh DESC, Infra_Score DESC
LIMIT 20;

-- @id: Q28
-- @section: Investment Deep-Dive
-- @title: States ranked by projected appreciation (window ranking)
-- @insight: State-level appreciation is tightly clustered; use the rank only as a tie-breaker.
SELECT RANK() OVER (ORDER BY AVG(Annual_Appreciation) DESC) AS rank_no,
       State, COUNT(*) AS properties,
       ROUND(100.0 * AVG(Annual_Appreciation), 2) AS avg_appreciation_pct,
       ROUND(AVG(Projected_Gain_Lakhs), 1)        AS avg_gain_lakhs
FROM properties
GROUP BY State
ORDER BY rank_no;

-- @id: Q29
-- @section: Investment Deep-Dive
-- @title: Share of each city's listings priced below the city median (CTE)
-- @insight: By construction ~50 % of any city sits below its median - the real edge is picking those with strong infrastructure too.
WITH city_med AS (
  SELECT City, MAX(City_Median_PPSF) AS median_ppsf FROM properties GROUP BY City)
SELECT p.City, m.median_ppsf,
       ROUND(100.0 * AVG(p.Price_per_SqFt_INR < m.median_ppsf), 1)                            AS pct_below_median,
       ROUND(100.0 * AVG(CASE WHEN p.Price_per_SqFt_INR < m.median_ppsf
                               AND p.Infra_Score >= 70 THEN 1 ELSE 0 END), 1)                 AS pct_cheap_and_high_infra
FROM properties p JOIN city_med m ON m.City = p.City
GROUP BY p.City, m.median_ppsf
ORDER BY pct_cheap_and_high_infra DESC
LIMIT 10;

-- @id: Q30
-- @section: Investment Deep-Dive
-- @title: Good-Investment rate by property type and BHK (pivot)
-- @insight: Configuration (type x BHK) has almost no effect on the Good-Investment rate (all cells ~39 %).
SELECT Property_Type,
       ROUND(100.0 * AVG(CASE WHEN BHK = 1 THEN Good_Investment END), 1) AS bhk_1,
       ROUND(100.0 * AVG(CASE WHEN BHK = 2 THEN Good_Investment END), 1) AS bhk_2,
       ROUND(100.0 * AVG(CASE WHEN BHK = 3 THEN Good_Investment END), 1) AS bhk_3,
       ROUND(100.0 * AVG(CASE WHEN BHK = 4 THEN Good_Investment END), 1) AS bhk_4,
       ROUND(100.0 * AVG(CASE WHEN BHK = 5 THEN Good_Investment END), 1) AS bhk_5
FROM properties
GROUP BY Property_Type;

-- @id: Q31
-- @section: Investment Deep-Dive
-- @title: Building age band vs investment quality
-- @insight: MODELLED: newer buildings project higher appreciation, but the effect is smaller than valuation.
SELECT Age_Band, COUNT(*) AS properties,
       ROUND(AVG(Price_per_SqFt_INR)) AS avg_ppsf_inr,
       ROUND(100.0 * AVG(Annual_Appreciation), 2) AS avg_appreciation_pct,
       ROUND(100.0 * AVG(Good_Investment), 1)     AS good_investment_pct
FROM properties
GROUP BY Age_Band
ORDER BY MIN(Age_of_Property);

-- @id: Q32
-- @section: Investment Deep-Dive
-- @title: Projected 5-year wealth creation by price band (with cumulative share)
-- @insight: Cheaper bands show higher projected % growth (below city median); pricier bands add more absolute rupees (see cumulative share).
WITH band AS (
  SELECT Price_Band, MIN(Price_in_Lakhs) AS lo, COUNT(*) AS properties,
         ROUND(AVG(Projected_Gain_Lakhs), 1)          AS avg_gain_lakhs,
         ROUND(100.0 * AVG(Annual_Appreciation), 2)   AS avg_appreciation_pct,
         SUM(Projected_Gain_Lakhs)                    AS total_gain
  FROM properties GROUP BY Price_Band)
SELECT Price_Band, properties, avg_gain_lakhs, avg_appreciation_pct,
       ROUND(100.0 * SUM(total_gain) OVER (ORDER BY lo) / SUM(total_gain) OVER (), 1) AS cumulative_gain_share_pct
FROM band
ORDER BY lo;

-- @id: Q33
-- @section: Investment Deep-Dive
-- @title: Ideal-buyer screen - Good Investments with high infrastructure and transit
-- @insight: A ready-made filter for the property finder: Good Investments with high infrastructure, high transit and below-median price.
SELECT State, COUNT(*) AS qualifying_properties,
       ROUND(AVG(Price_in_Lakhs), 1)        AS avg_price_lakhs,
       ROUND(AVG(Future_Price_5Y_Lakhs), 1) AS avg_future_price_lakhs
FROM properties
WHERE Good_Investment = 1
  AND Infra_Score >= 70
  AND Public_Transport_Accessibility = 'High'
  AND Value_Ratio <= 1.0
GROUP BY State
ORDER BY qualifying_properties DESC
LIMIT 10;
