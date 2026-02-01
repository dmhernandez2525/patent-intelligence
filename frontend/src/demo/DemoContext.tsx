import { createContext, useContext, useState, type ReactNode } from 'react'

interface DemoContextType {
  isDemo: boolean
  setIsDemo: (value: boolean) => void
}

const DemoContext = createContext<DemoContextType | undefined>(undefined)

export function DemoProvider({ children }: { children: ReactNode }) {
  const [isDemo, setIsDemo] = useState(false)

  return (
    <DemoContext.Provider value={{ isDemo, setIsDemo }}>
      {children}
    </DemoContext.Provider>
  )
}

export function useDemo() {
  const context = useContext(DemoContext)
  if (context === undefined) {
    throw new Error('useDemo must be used within a DemoProvider')
  }
  return context
}

export function useDemoMode() {
  const context = useContext(DemoContext)
  return context?.isDemo ?? false
}
