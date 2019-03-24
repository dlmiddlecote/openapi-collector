/*

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package service

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller"
	"sigs.k8s.io/controller-runtime/pkg/handler"
	"sigs.k8s.io/controller-runtime/pkg/manager"
	"sigs.k8s.io/controller-runtime/pkg/reconcile"
	"sigs.k8s.io/controller-runtime/pkg/source"
)

const (
	annotationCollect string = "openapi/collect"
	annotationPath    string = "openapi/path"
	annotationPort    string = "openapi/port"

	finalizer string = "openapi/finalizer"

	configmapNginx   string = "openapi-collector-nginx-dynamic-config"
	configmapSwagger string = "openapi-collector-swagger-dynamic-config"

	nginxUpstreamTmpl string = `
        upstream %s {
          server %s.%s:%s;
        }
	`
	nginxLocationTmpl string = `
        location /%s {
          rewrite /%s/(.*) /$1 break;
          proxy_pass http://%s;
        }
	`
)

type swaggerURL struct {
	Name string `json:"name"`
	URL  string `json:"url"`
}

type swaggerConfig struct {
	URLs []swaggerURL `json:"urls"`
}

// Add creates a new Service Controller and adds it to the Manager with default RBAC. The Manager will set fields on the Controller
// and Start it when the Manager is Started.
func Add(mgr manager.Manager) error {
	return add(mgr, newReconciler(mgr))
}

// newReconciler returns a new reconcile.Reconciler
func newReconciler(mgr manager.Manager) reconcile.Reconciler {
	return &ReconcileService{Client: mgr.GetClient(), scheme: mgr.GetScheme()}
}

// add adds a new Controller to mgr with r as the reconcile.Reconciler
func add(mgr manager.Manager, r reconcile.Reconciler) error {
	// Create a new controller
	c, err := controller.New("service-controller", mgr, controller.Options{Reconciler: r})
	if err != nil {
		return err
	}

	// Watch for changes to Service
	err = c.Watch(&source.Kind{Type: &corev1.Service{}}, &handler.EnqueueRequestForObject{})
	if err != nil {
		return err
	}

	// TODO(user): Modify this to be the types you create
	// Uncomment watch a Deployment created by Service - change this for objects you create
	// err = c.Watch(&source.Kind{Type: &appsv1.Deployment{}}, &handler.EnqueueRequestForOwner{
	//     IsController: true,
	//     OwnerType:    &corev1.Service{},
	// })
	// if err != nil {
	//     return err
	// }

	return nil
}

var _ reconcile.Reconciler = &ReconcileService{}

// ReconcileService reconciles a Service object
type ReconcileService struct {
	client.Client
	scheme *runtime.Scheme
}

// Reconcile reads that state of the cluster for a Service object and makes changes based on the state read
// and what is in the Service.Spec
// +kubebuilder:rbac:groups=core,resources=services,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=services/status,verbs=get;update;patch
func (r *ReconcileService) Reconcile(request reconcile.Request) (reconcile.Result, error) {
	// Fetch the Service instance
	instance := &corev1.Service{}
	err := r.Get(context.TODO(), request.NamespacedName, instance)
	if err != nil {
		if errors.IsNotFound(err) {
			// Object not found, return.  Created objects are automatically garbage collected.
			// For additional cleanup logic use finalizers.
			return reconcile.Result{}, nil
		}
		// Error reading the object - requeue the request.
		return reconcile.Result{}, err
	}

	ctx := context.TODO()

	// has service been deleted
	deleted := instance.GetDeletionTimestamp() != nil

	// get finalizers
	pendingFinalizers := instance.GetFinalizers()
	finalizerExists := false
	for _, s := range pendingFinalizers {
		if s == finalizer {
			finalizerExists = true
		}
	}

	// get configmaps
	cmNginx, err := r.getConfigmap(request.Namespace, configmapNginx)
	if err != nil {
		return reconcile.Result{}, err
	}
	if cmNginx == nil {
		return reconcile.Result{}, nil
	}

	cmSwagger, err := r.getConfigmap(request.Namespace, configmapSwagger)
	if err != nil {
		return reconcile.Result{}, err
	}
	if cmSwagger == nil {
		return reconcile.Result{}, nil
	}

	// check for existence of annotation
	annotations := instance.Annotations
	collect, annotationExists := annotations[annotationCollect]

	if !deleted && annotationExists && collect == "true" {
		// this is a service we care about, let's add it to the configmaps
		updateNginxConfigmap(instance, annotations, cmNginx)
		updateSwaggerConfigmap(instance, annotations, cmSwagger)

		// store updates
		err = r.Update(ctx, cmNginx)
		if err != nil {
			return reconcile.Result{}, err
		}

		err = r.Update(ctx, cmSwagger)
		if err != nil {
			return reconcile.Result{}, err
		}

		// add finalizer
		if !finalizerExists {
			finalizers := append(pendingFinalizers, finalizer)
			instance.SetFinalizers(finalizers)
			err = r.Update(ctx, instance)
			if err != nil {
				return reconcile.Result{}, err
			}
		}
	} else {
		// remove config
		removeFromNginxConfig(instance, cmNginx)
		removeFromSwaggerConfig(instance, cmSwagger)

		// store updates
		err = r.Update(ctx, cmNginx)
		if err != nil {
			return reconcile.Result{}, err
		}

		err = r.Update(ctx, cmSwagger)
		if err != nil {
			return reconcile.Result{}, err
		}

		// remove finalizer
		if finalizerExists {
			finalizers := []string{}
			for _, s := range pendingFinalizers {
				if s != finalizer {
					finalizers = append(finalizers, s)
				}
			}

			// store finalizers
			instance.SetFinalizers(finalizers)
			err = r.Update(ctx, instance)
			if err != nil {
				return reconcile.Result{}, err
			}
		}
	}

	return reconcile.Result{}, nil
}

func (r *ReconcileService) getConfigmap(namespace, name string) (*corev1.ConfigMap, error) {
	cm := &corev1.ConfigMap{}
	err := r.Get(context.TODO(), types.NamespacedName{Name: name, Namespace: namespace}, cm)
	if err != nil {
		if errors.IsNotFound(err) {
			// TODO: create cm
			return nil, nil
		}
		return nil, err
	}

	return cm, nil
}

func updateNginxConfigmap(svc *corev1.Service, annotations map[string]string, cm *corev1.ConfigMap) {
	// get port
	specPort, ok := annotations[annotationPort]
	if !ok || specPort == "" {
		// use default port
		specPort = "80"
	}

	if _, err := strconv.Atoi(specPort); err != nil {
		// port is not an integer, assume it is name of port in service
		for _, port := range svc.Spec.Ports {
			if port.Name == specPort {
				specPort = fmt.Sprintf("%d", port.Port)
				break
			}
		}

		// if still not an integer, return
		if _, err := strconv.Atoi(specPort); err != nil {
			return
		}
	}

	host := fmt.Sprintf("%s-%s", svc.Name, svc.Namespace)
	fileNameUpstream := fmt.Sprintf("%s-upstream.conf", host)
	cm.Data[fileNameUpstream] = fmt.Sprintf(nginxUpstreamTmpl, host, svc.Name, svc.Namespace, specPort)
	fileNameLocation := fmt.Sprintf("%s-location.conf", host)
	cm.Data[fileNameLocation] = fmt.Sprintf(nginxLocationTmpl, host, host, host)
}

func updateSwaggerConfigmap(svc *corev1.Service, annotations map[string]string, cm *corev1.ConfigMap) {
	// get path
	specPath, ok := annotations[annotationPath]
	if !ok || specPath == "" {
		// use default path
		specPath = "/openapi.json"
	}

	if !strings.HasPrefix(specPath, "/") {
		specPath = fmt.Sprintf("/%s", specPath)
	}

	confKey := "swagger-config.json"

	// unmarshal conf
	swaggerConfText := cm.Data[confKey]
	swaggerConf := &swaggerConfig{}
	err := json.Unmarshal([]byte(swaggerConfText), swaggerConf)
	if err != nil {
		return
	}

	host := fmt.Sprintf("%s-%s", svc.Name, svc.Namespace)
	// remove existing url for host
	urls := []swaggerURL{}
	for _, u := range swaggerConf.URLs {
		if u.Name != host {
			urls = append(urls, u)
		}
	}

	// add new url
	urls = append(urls, swaggerURL{Name: host, URL: fmt.Sprintf("/%s%s", host, specPath)})

	// re-marshal json
	newConf, err := json.Marshal(swaggerConfig{URLs: urls})
	if err != nil {
		return
	}

	cm.Data[confKey] = string(newConf)
}

func removeFromNginxConfig(svc *corev1.Service, cm *corev1.ConfigMap) {
	fileNameUpstream := fmt.Sprintf("%s-%s-upstream.conf", svc.Name, svc.Namespace)
	fileNameLocation := fmt.Sprintf("%s-%s-location.conf", svc.Name, svc.Namespace)
	for _, fn := range []string{fileNameUpstream, fileNameLocation} {
		if _, ok := cm.Data[fn]; ok {
			delete(cm.Data, fn)
		}
	}
}

func removeFromSwaggerConfig(svc *corev1.Service, cm *corev1.ConfigMap) {
	confKey := "swagger-config.json"

	// unmarshal conf
	swaggerConfText := cm.Data[confKey]
	swaggerConf := &swaggerConfig{}
	err := json.Unmarshal([]byte(swaggerConfText), swaggerConf)
	if err != nil {
		return
	}

	host := fmt.Sprintf("%s-%s", svc.Name, svc.Namespace)
	// remove existing url for host
	urls := []swaggerURL{}
	for _, u := range swaggerConf.URLs {
		if u.Name != host {
			urls = append(urls, u)
		}
	}

	// re-marshal json
	newConf, err := json.Marshal(swaggerConfig{URLs: urls})
	if err != nil {
		return
	}

	cm.Data[confKey] = string(newConf)
}
