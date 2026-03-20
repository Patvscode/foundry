import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  Outlet,
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
  useParams,
} from '@tanstack/react-router'

import { Shell } from '@/components/layout/Shell'
import { DashboardRoute } from '@/routes'
import { OnboardingRoute } from '@/routes/onboarding'
import { ProjectWorkspaceRoute } from '@/routes/project.$id'
import { SettingsRoute } from '@/routes/settings'
import { SubprojectRoute } from '@/routes/subproject.$id'

const queryClient = new QueryClient()

function RootLayout() {
  return (
    <Shell>
      <Outlet />
    </Shell>
  )
}

const rootRoute = createRootRoute({
  component: RootLayout,
})

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: DashboardRoute,
})

const onboardingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/onboarding',
  component: OnboardingRoute,
})

const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/settings',
  component: SettingsRoute,
})

function ProjectRouteWrapper() {
  const { id } = useParams({ from: '/project/$id' })
  return <ProjectWorkspaceRoute id={id} />
}

const projectRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/project/$id',
  component: ProjectRouteWrapper,
})

function SubprojectRouteWrapper() {
  const { id } = useParams({ from: '/subproject/$id' })
  return <SubprojectRoute id={id} />
}

const subprojectRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/subproject/$id',
  component: SubprojectRouteWrapper,
})

const routeTree = rootRoute.addChildren([dashboardRoute, projectRoute, subprojectRoute, onboardingRoute, settingsRoute])

const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
