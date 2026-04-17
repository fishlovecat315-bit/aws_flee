import { useState, useMemo } from 'react'
import { Radio, Card } from 'antd'
import ReactECharts from 'echarts-for-react'
import type { DailyCostItem, MonthlyCostItem } from '../types'

interface CostChartProps {
  data: DailyCostItem[] | MonthlyCostItem[]
  granularity: 'daily' | 'monthly'
}

type ChartType = 'line' | 'bar' | 'pie'

function isDailyItem(item: DailyCostItem | MonthlyCostItem): item is DailyCostItem {
  return 'date' in item
}

export default function CostChart({ data, granularity }: CostChartProps) {
  const [chartType, setChartType] = useState<ChartType>('line')

  const option = useMemo(() => {
    if (data.length === 0) return {}

    const dateKey = granularity === 'daily' ? 'date' : 'year_month'

    // Collect unique dates and departments
    const datesSet = new Set<string>()
    const deptsSet = new Set<string>()
    data.forEach((item) => {
      const d = isDailyItem(item) ? item.date : item.year_month
      datesSet.add(d)
      deptsSet.add(item.department)
    })
    const dates = Array.from(datesSet).sort()
    const depts = Array.from(deptsSet).sort()

    if (chartType === 'pie') {
      // Aggregate by department
      const totals: Record<string, number> = {}
      data.forEach((item) => {
        totals[item.department] = (totals[item.department] ?? 0) + Number(item.amount_usd)
      })
      return {
        tooltip: { trigger: 'item', formatter: '{b}: ${c} ({d}%)' },
        legend: { orient: 'vertical', left: 'left' },
        series: [
          {
            type: 'pie',
            radius: '60%',
            data: Object.entries(totals).map(([name, value]) => ({
              name,
              value: Number(value.toFixed(2)),
            })),
            emphasis: {
              itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' },
            },
          },
        ],
      }
    }

    // Build amount map: dept -> date -> amount
    const amountMap: Record<string, Record<string, number>> = {}
    data.forEach((item) => {
      const d = isDailyItem(item) ? item.date : item.year_month
      if (!amountMap[item.department]) amountMap[item.department] = {}
      amountMap[item.department][d] = (amountMap[item.department][d] ?? 0) + Number(item.amount_usd)
    })

    const series = depts.map((dept) => ({
      name: dept,
      type: chartType,
      data: dates.map((d) => Number((amountMap[dept]?.[d] ?? 0).toFixed(2))),
      smooth: chartType === 'line',
    }))

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: depts, bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { rotate: dates.length > 10 ? 30 : 0 },
      },
      yAxis: {
        type: 'value',
        axisLabel: { formatter: '${value}' },
      },
      series,
    }
  }, [data, granularity, chartType])

  return (
    <Card
      title="费用趋势图"
      extra={
        <Radio.Group
          value={chartType}
          onChange={(e) => setChartType(e.target.value as ChartType)}
          optionType="button"
          buttonStyle="solid"
          size="small"
        >
          <Radio.Button value="line">折线图</Radio.Button>
          <Radio.Button value="bar">柱状图</Radio.Button>
          <Radio.Button value="pie">饼图</Radio.Button>
        </Radio.Group>
      }
      style={{ marginBottom: 16 }}
    >
      {data.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
      ) : (
        <ReactECharts option={option} style={{ height: 360 }} notMerge />
      )}
    </Card>
  )
}
