"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Chart } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend);

export type CoutViePoint = {
  state_code: string;
  cost_of_living_index: number;
  note_moyenne_etat: number;
};

export default function CoutVieChart({ data }: { data: CoutViePoint[] }) {
  return (
    <Chart
      type="bar"
      data={{
        labels: data.map((d) => d.state_code),
        datasets: [
          {
            type: "bar" as const,
            label: "Indice coût de la vie (100 = moyenne US)",
            data: data.map((d) => d.cost_of_living_index),
            backgroundColor: "#f87171",
            yAxisID: "y",
          },
          {
            type: "line" as const,
            label: "Note moyenne / 5",
            data: data.map((d) => d.note_moyenne_etat),
            borderColor: "#0f172a",
            backgroundColor: "#0f172a",
            yAxisID: "y1",
            tension: 0.3,
          },
        ],
      }}
      options={{
        responsive: true,
        plugins: { legend: { position: "top" as const } },
        scales: {
          y: {
            type: "linear",
            position: "left",
            title: { display: true, text: "Indice coût de la vie" },
          },
          y1: {
            type: "linear",
            position: "right",
            min: 0,
            max: 5,
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Note / 5" },
          },
        },
      }}
    />
  );
}
