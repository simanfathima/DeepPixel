import torch
import torch.nn.functional as F

class SSCAM1(BaseCAM):

    """
        SSCAM1, inherit from BaseCAM
    """

    def __init__(self, model_dict):
        super().__init__(model_dict)

    def forward(self, input, class_idx=None, param_n=35, mean=0, sigma=2, retain_graph=False):
        b, c, h, w = input.size()
        
        # prediction on raw input
        logit = self.model_arch(input)
        
        if class_idx is None:
            predicted_class = logit.max(1)[-1]
            score = logit[:, logit.max(1)[-1]].squeeze()
        else:
            predicted_class = torch.LongTensor([class_idx])
            score = logit[:, class_idx].squeeze()
        
        logit = F.softmax(logit)

        if torch.cuda.is_available():
          predicted_class= predicted_class.cuda()
          score = score.cuda()
          logit = logit.cuda()

        self.model_arch.zero_grad()
        score.backward(retain_graph=retain_graph)
        activations = self.activations['value']
        b1, k, u, v = activations.size()
        
        score_saliency_map = torch.zeros((1, 1, h, w))

        if torch.cuda.is_available():
          activations = activations.cuda()
          score_saliency_map = score_saliency_map.cuda()

        #HYPERPARAMETERS (can be modified for better/faster explanations)
        #mean = 0
        #param_n = 35
        #param_sigma_multiplier = 2
        

        with torch.no_grad():
          for i in range(k):

              # upsampling
              saliency_map = torch.unsqueeze(activations[:, i, :, :], 1)
              
              saliency_map = F.interpolate(saliency_map, size=(h, w), mode='bilinear', align_corners=False)
 
              if saliency_map.max() == saliency_map.min():
                continue

              x = saliency_map               

              if (torch.max(x) - torch.min(x)).item() == 0:
                continue
              else:
                sigma = param_sigma_multiplier / (torch.max(x) - torch.min(x)).item()
              
              score_list = []
              noisy_list = []
              
              # Adding noise to the upsampled activation map `x`
              for _ in range(param_n):

                noise = Variable(x.data.new(x.size()).normal_(mean, sigma**2))
                
                noisy_img = x + noise

                noisy_list.append(noisy_img)
               
                output = self.model_arch(noisy_img * input)
                output = F.softmax(output)
                score = output[0][predicted_class]
                score_list.append(score)
              
              # Averaging the scores to introduce smoothing
              score = sum(score_list) / len(score_list)
              score_saliency_map +=  score * saliency_map
                
        score_saliency_map = F.relu(score_saliency_map)
        score_saliency_map_min, score_saliency_map_max = score_saliency_map.min(), score_saliency_map.max()

        if score_saliency_map_min == score_saliency_map_max:
            return None

        score_saliency_map = (score_saliency_map - score_saliency_map_min).div(score_saliency_map_max - score_saliency_map_min).data

        return score_saliency_map

    def __call__(self, input, class_idx=None, retain_graph=False):
        return self.forward(input, class_idx, retain_graph)


class SSCAM2(BaseCAM):

    """
        SSCAM2, inherit from BaseCAM

    """

    def __init__(self, model_dict):
        super().__init__(model_dict)

    def forward(self, input, class_idx=None, param_n=35, mean=0, sigma=2, retain_graph=False):
        b, c, h, w = input.size()
        
        # prediction on raw input
        logit = self.model_arch(input)
        
        if class_idx is None:
            predicted_class = logit.max(1)[-1]
            score = logit[:, logit.max(1)[-1]].squeeze()
        else:
            predicted_class = torch.LongTensor([class_idx])
            score = logit[:, class_idx].squeeze()
        
        logit = F.softmax(logit)

        if torch.cuda.is_available():
          predicted_class= predicted_class.cuda()
          score = score.cuda()
          logit = logit.cuda()

        self.model_arch.zero_grad()
        score.backward(retain_graph=retain_graph)
        activations = self.activations['value']
        b1, k, u, v = activations.size()
        
        score_saliency_map = torch.zeros((1, 1, h, w))

        if torch.cuda.is_available():
          activations = activations.cuda()
          score_saliency_map = score_saliency_map.cuda()

        #HYPERPARAMETERS (can be modified for better/faster explanations)
        #mean = 0
        #param_n = 35
        #param_sigma_multiplier = 2
        

        with torch.no_grad():
          for i in range(k):

              # upsampling
              saliency_map = torch.unsqueeze(activations[:, i, :, :], 1)
              
              saliency_map = F.interpolate(saliency_map, size=(h, w), mode='bilinear', align_corners=False)

              if saliency_map.max() == saliency_map.min():
                continue

              # Normalization
              norm_saliency_map = (saliency_map - saliency_map.min()) / (saliency_map.max() - saliency_map.min())

              x = input * norm_saliency_map              

              if (torch.max(x) - torch.min(x)).item() == 0:
                continue
              else:
                sigma = param_sigma_multiplier / (torch.max(x) - torch.min(x)).item()
              
              score_list = []
              noisy_list = []

              # Adding noise to the normalized input mask `x`
              for i in range(param_n):

                noise = Variable(x.data.new(x.size()).normal_(mean, sigma**2))
                
                noisy_img = x + noise

                noisy_list.append(noisy_img)
                
                noisy_img = noisy_img.cuda()
                output = self.model_arch(noisy_img)
                output = F.softmax(output)
                score = output[0][predicted_class]
                score_list.append(score)

              # Averaging the scores to introduce smoothing               
              score = sum(score_list) / len(score_list)
              score_saliency_map +=  score * saliency_map
                
        score_saliency_map = F.relu(score_saliency_map)
        score_saliency_map_min, score_saliency_map_max = score_saliency_map.min(), score_saliency_map.max()

        if score_saliency_map_min == score_saliency_map_max:
            return None

        score_saliency_map = (score_saliency_map - score_saliency_map_min).div(score_saliency_map_max - score_saliency_map_min).data

        return score_saliency_map

    def __call__(self, input, class_idx=None, retain_graph=False):
        return self.forward(input, class_idx, retain_graph)