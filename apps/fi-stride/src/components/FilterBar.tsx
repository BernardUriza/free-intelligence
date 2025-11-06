import styles from '../styles/library.module.css'

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
    <div className={styles.controls}>
      {/* Search Input */}
      <input
        type="text"
        placeholder={searchPlaceholder}
        value={searchValue}
        onChange={(e) => onSearchChange(e.target.value)}
        className={styles.searchInput}
        aria-label="Search input"
      />

      {/* Filter Buttons */}
      {filters && filters.length > 0 && (
        <div className={styles.filterButtons}>
          {filters.map((filter) => (
            <button
              key={filter.id}
              className={`${styles.filterBtn} ${
                activeFilter === filter.id ? styles.active : ''
              }`}
              onClick={() => onFilterChange?.(filter.id)}
              aria-pressed={activeFilter === filter.id}
              type="button"
            >
              {filter.icon && <span>{filter.icon}</span>}
              {filter.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
