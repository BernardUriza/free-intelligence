export interface FilterOption {
  id: string
  label: string
  icon?: string
}

export interface FilterBarProps {
  /**
   * Placeholder text for search input
   */
  searchPlaceholder?: string

  /**
   * Current search value
   */
  searchValue: string

  /**
   * Callback when search value changes
   */
  onSearchChange: (value: string) => void

  /**
   * Available filter options
   */
  filters?: FilterOption[]

  /**
   * Currently active filter
   */
  activeFilter?: string

  /**
   * Callback when filter is selected
   */
  onFilterChange?: (filterId: string) => void
}

/**
 * Reusable FilterBar component for search + filter UI
 * Used by Library and other pages that need filtering
 *
 * @example
 * <FilterBar
 *   searchValue={search}
 *   onSearchChange={setSearch}
 *   filters={[
 *     { id: 'all', label: 'Todas' },
 *     { id: 'recent', label: 'Recientes' },
 *   ]}
 *   activeFilter={filter}
 *   onFilterChange={setFilter}
 * />
 */
export function FilterBar({
  searchPlaceholder = '🔍 Buscar...',
  searchValue,
  onSearchChange,
  filters,
  activeFilter,
  onFilterChange
}: FilterBarProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-4 mb-6">
      {/* Search Input */}
      <input
        type="text"
        placeholder={searchPlaceholder}
        value={searchValue}
        onChange={(e) => onSearchChange(e.target.value)}
        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none transition"
        aria-label="Search input"
      />

      {/* Filter Buttons */}
      {filters && filters.length > 0 && (
        <div className="flex gap-2 flex-wrap sm:flex-nowrap">
          {filters.map((filter) => (
            <button
              key={filter.id}
              onClick={() => onFilterChange?.(filter.id)}
              aria-pressed={activeFilter === filter.id}
              type="button"
              className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 whitespace-nowrap ${
                activeFilter === filter.id
                  ? 'bg-blue-600 text-white ring-2 ring-blue-400'
                  : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
              }`}
            >
              {filter.icon && <span className="mr-2">{filter.icon}</span>}
              {filter.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
