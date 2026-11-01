// Licensed under the MIT License
#include "CameraServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace {CameraServices* services=nullptr;}
CameraServices* BindCameraServices(CameraServices* next)
{auto* previous=services;services=next;return previous;}
CameraServices& GetCameraServices()
{if(!services) throw std::logic_error("Production camera services are not bound");return *services;}
}
