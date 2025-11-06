import { render, screen, fireEvent } from '@testing-library/react'
import { FilterBar } from '../FilterBar'

describe('FilterBar', () => {
  it('should render search input', () => {
    render(
      <FilterBar
        searchValue=""
        onSearchChange={() => {}}
        searchPlaceholder="Search..."
      />
    )

    const input = screen.getByPlaceholderText('Search...')
    expect(input).toBeInTheDocument()
  })

  it('should call onSearchChange when input changes', () => {
    const handleChange = vi.fn()
    render(
      <FilterBar
        searchValue=""
        onSearchChange={handleChange}
        searchPlaceholder="Search..."
      />
    )

    const input = screen.getByPlaceholderText('Search...')
    fireEvent.change(input, { target: { value: 'test' } })

    expect(handleChange).toHaveBeenCalledWith('test')
  })

  it('should render filter buttons', () => {
    const filters = [
      { id: 'all', label: 'All' },
      { id: 'recent', label: 'Recent' },
      { id: 'archived', label: 'Archived' }
    ]

    render(
      <FilterBar
        searchValue=""
        onSearchChange={() => {}}
        filters={filters}
        activeFilter="all"
      />
    )

    expect(screen.getByText('All')).toBeInTheDocument()
    expect(screen.getByText('Recent')).toBeInTheDocument()
    expect(screen.getByText('Archived')).toBeInTheDocument()
  })

  it('should highlight active filter', () => {
    const filters = [
      { id: 'all', label: 'All' },
      { id: 'recent', label: 'Recent' }
    ]

    const { container } = render(
      <FilterBar
        searchValue=""
        onSearchChange={() => {}}
        filters={filters}
        activeFilter="recent"
      />
    )

    const buttons = container.querySelectorAll('button')
    const recentBtn = buttons[1] // Second button

    expect(recentBtn).toHaveClass('active')
  })

  it('should call onFilterChange when filter button is clicked', () => {
    const handleFilterChange = vi.fn()
    const filters = [
      { id: 'all', label: 'All' },
      { id: 'recent', label: 'Recent' }
    ]

    render(
      <FilterBar
        searchValue=""
        onSearchChange={() => {}}
        filters={filters}
        activeFilter="all"
        onFilterChange={handleFilterChange}
      />
    )

    const recentBtn = screen.getByText('Recent')
    fireEvent.click(recentBtn)

    expect(handleFilterChange).toHaveBeenCalledWith('recent')
  })

  it('should render filter icons if provided', () => {
    const filters = [
      { id: 'all', label: 'All', icon: '🌟' },
      { id: 'recent', label: 'Recent', icon: '📅' }
    ]

    render(
      <FilterBar
        searchValue=""
        onSearchChange={() => {}}
        filters={filters}
        activeFilter="all"
      />
    )

    expect(screen.getByText('🌟')).toBeInTheDocument()
    expect(screen.getByText('📅')).toBeInTheDocument()
  })
})
