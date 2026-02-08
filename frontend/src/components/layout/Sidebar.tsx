import { useCategories } from "@/hooks/useEvents";
import { useFilterStore } from "@/store/filterStore";

export default function Sidebar() {
  const categories = useCategories();
  const { activeCategories, toggleCategory, searchQuery, setSearchQuery } =
    useFilterStore();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 p-4 flex flex-col gap-4 overflow-y-auto">
      <div>
        <label className="block text-xs font-semibold text-gray-500 uppercase mb-2">
          Search
        </label>
        <input
          type="text"
          placeholder="Search events..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-gray-500 uppercase mb-2">
          Categories
        </label>
        <div className="space-y-1">
          {categories.map((cat) => (
            <label key={cat.id} className="flex items-center gap-2 cursor-pointer py-1">
              <input
                type="checkbox"
                checked={activeCategories.length === 0 || activeCategories.includes(cat.id)}
                onChange={() => toggleCategory(cat.id, categories.map((c) => c.id))}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: cat.color }}
              />
              <span className="text-sm text-gray-700">{cat.name}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-gray-500 uppercase mb-2">
          Country
        </label>
        <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
          United States
        </div>
      </div>
    </aside>
  );
}
