import Link from "next/link";
import { Thermometer } from "lucide-react";
import { cityImage, tempWord } from "@/lib/agency";
import { ScenicImage } from "@/components/agency/scenic-image";

export type CityWeather = { id: string; name: string; country_code: string; temp: number | null; stale: boolean };

export function DestinationCard({ city }: { city: CityWeather }) {
  return (
    <Link href={`/destinations/${city.id}`} className="group overflow-hidden rounded-xl border bg-card transition-shadow hover:shadow-md">
      <ScenicImage src={cityImage(city.name)} alt={city.name} className="aspect-[4/3]" />
      <div className="flex items-center justify-between p-4">
        <div>
          <h3 className="font-semibold group-hover:underline">{city.name}</h3>
          <p className="text-xs text-muted-foreground">{city.country_code}</p>
        </div>
        {city.temp !== null ? (
          <div className="text-right">
            <div className="inline-flex items-center gap-1 text-lg font-medium"><Thermometer className="size-4 text-muted-foreground" />{Math.round(city.temp)}°</div>
            <div className="text-xs text-muted-foreground">{tempWord(city.temp)} now{city.stale ? ", older reading" : ""}</div>
          </div>
        ) : (
          <div className="text-xs text-muted-foreground">no reading yet</div>
        )}
      </div>
    </Link>
  );
}
