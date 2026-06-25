# LLD — Site Detail Timeseries Data History

* **Stage 3 of 3 — Documentation Hierarchy**
* **Owner**: Winston (Architect) / Amelia (Developer)
* **Feature Initiative**: Collapsible inline timeseries line charts for raw parameters and score breakdowns in the Site Detail Drawer.

---

## 1. Backend Endpoint & Schemas

### 1.1 Pydantic Schemas (`backend/app/schemas/spatial.py`)
Add dynamic historical schema wrappers that match the decoupled analysis layer:

```python
class GenericSamplingHistory(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the sampling record")
    sampled_at: datetime = Field(..., description="Timestamp when the sample was taken")
    parameters: dict[str, Any] = Field(..., description="Domain-specific raw parameter key-value pairs")

    model_config = ConfigDict(from_attributes=True)


class GenericScoreHistory(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the health score")
    calculated_at: datetime = Field(..., description="Timestamp when the score was calculated")
    composite_score: Decimal = Field(..., description="Pre-adjustment composite score")
    ik_signal_value: Decimal = Field(..., description="Indigenous knowledge signal value")
    adjusted_score: Decimal = Field(..., description="Fuzzy-adjusted composite score")
    health_class: str = Field(..., description="Wetland health class (A-E)")
    breakdown: dict[str, Any] = Field(..., description="Domain-specific score breakdown key-value pairs")

    model_config = ConfigDict(from_attributes=True)
```

### 1.2 Router Implementation (`backend/app/routers/public_router.py`)
Add the endpoint `/sites/{site_id}/samplings`:

```python
@router.get(
    "/sites/{site_id}/samplings", response_model=List[schemas.GenericSamplingHistory]
)
@limiter.limit("60/minute")
def get_site_samplings(
    request: Request,
    site_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    # Resolve Site ID/Code
    try:
        val = uuid.UUID(site_id)
        db_site = db.query(Site).filter(Site.id == val).first()
    except ValueError:
        db_site = db.query(Site).filter(Site.code == site_id).first()

    if not db_site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")

    query = db.query(SamplingRecord).filter(SamplingRecord.site_id == db_site.id)

    # Default to 30 days ago if no date_from is passed
    if not date_from:
        date_from = datetime.utcnow() - timedelta(days=30)
    query = query.filter(SamplingRecord.sampled_at >= date_from)

    if date_to:
        query = query.filter(SamplingRecord.sampled_at <= date_to)

    samplings = (
        query.order_by(SamplingRecord.sampled_at.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return samplings
```

---

## 2. Frontend API Client & Types

### 2.1 Interface Definitions (`frontend/src/lib/api.ts`)
Add TypeScript definitions:

```typescript
export interface GenericSamplingHistory {
  id: string;
  sampled_at: string;
  parameters: Record<string, any>;
}

export interface GenericScoreHistory {
  id: string;
  calculated_at: string;
  composite_score: number;
  ik_signal_value: number;
  adjusted_score: number;
  health_class: string;
  breakdown: Record<string, any>;
}
```

### 2.2 Fetch Implementations
Add endpoints in `frontend/src/lib/api.ts`:
```typescript
export async function fetchSiteSamplings(
  siteId: string,
  dateFrom?: string,
  dateTo?: string
): Promise<GenericSamplingHistory[]> {
  const params = new URLSearchParams();
  if (dateFrom) params.append("date_from", dateFrom);
  if (dateTo) params.append("date_to", dateTo);
  
  const res = await fetch(`/api/v1/sites/${siteId}/samplings?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch site samplings history");
  return res.json();
}
```

---

## 3. UI Component Integration (`frontend/src/components/ui/site-drawer.tsx`)

### 3.1 Fetch Hooks
Fetch both lists inside a `useEffect` keyed on `site.id`:
```typescript
const [samplingsHistory, setSamplingsHistory] = useState<GenericSamplingHistory[]>([]);
const [scoresHistory, setScoresHistory] = useState<GenericScoreHistory[]>([]);

useEffect(() => {
  if (!site?.id) return;
  
  // Fetch past 30 days of data
  const dateFrom = new Date();
  dateFrom.setDate(dateFrom.getDate() - 30);
  const dateFromStr = dateFrom.toISOString();

  fetchSiteSamplings(site.id, dateFromStr).then(setSamplingsHistory).catch(console.error);
  fetchSiteScores(site.id, dateFromStr).then(setScoresHistory).catch(console.error);
}, [site?.id]);
```

### 3.2 Collapsible Container Pattern
We can use a custom React component/wrapper or Radix Collapsible elements:
```tsx
interface CollapsibleChartContainerProps {
  label: string;
  latestValue: string | number;
  unit?: string;
  data: { date: string; value: number }[];
}

export function CollapsibleChartContainer({ label, latestValue, unit, data }: CollapsibleChartContainerProps) {
  const [isOpen, setIsOpen] = useState(false);
  
  const chartOptions: echarts.EChartsOption = {
    tooltip: { trigger: "axis" },
    grid: { left: "10%", right: "10%", top: "15%", bottom: "15%" },
    xAxis: {
      type: "category",
      data: data.map(d => new Date(d.date).toLocaleDateString()),
    },
    yAxis: { type: "value" },
    series: [
      {
        data: data.map(d => d.value),
        type: "line",
        smooth: true,
        color: "#0ea5e9", // Sky-500
      }
    ]
  };

  return (
    <div className="border border-slate-100 rounded-xl bg-white overflow-hidden shadow-sm">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between text-slate-700 hover:bg-slate-50 transition-colors"
      >
        <span className="text-xs font-semibold">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-900">{latestValue} {unit}</span>
          <TrendingUp className="w-3.5 h-3.5 text-slate-400" />
        </div>
      </button>
      {isOpen && (
        <div className="h-44 px-4 pb-4 border-t border-slate-50 bg-slate-50/30">
          {data.length > 0 ? (
            <EChartsChart options={chartOptions} />
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400 italic">
              No historical data for this period
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## 4. Verification & Testing

### 4.1 Pytest Integration (`backend/tests/test_site_history.py`)
Verify endpoint output:
```python
def test_get_site_samplings_history(client, db_session, test_site):
    # Seed 3 sampling records
    ...
    response = client.get(f"/api/v1/sites/{test_site.id}/samplings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert "parameters" in data[0]
```

### 4.2 Vitest Component Mocking (`frontend/src/components/ui/__tests__/site-drawer.test.tsx`)
Verify chart opens on click:
* Mock `fetchSiteSamplings` and `fetchSiteScores` responses.
* Fire click event on the trend icon/button.
* Assert that the container expands and ECharts elements are initialized.
